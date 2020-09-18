# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
import math
import logging
from PIL import Image
import time
import json
import os

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ebaysdk.exception import ConnectionError
from ..tools.ebaysdk import Finding
#from odoo.addons.sale_ebay.tools.ebaysdk import Trading
from xml.sax.saxutils import escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.osv import expression
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError

_logger = logging.getLogger(__name__)

_30DAYS = timedelta(days=30)
# eBay api limits ItemRevise calls to 150 per day
MAX_REVISE_CALLS = 150
EBAY_DATEFORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def _ebay_parse_date(s):  # should be fromisoformat starting with datetime 3.7
    return datetime.strptime(s, EBAY_DATEFORMAT)


def _log_logging(env, message, function_name, path):
    env['ir.logging'].sudo().create({
        'name': 'eBay',
        'type': 'server',
        'level': 'DEBUG',
        'dbname': env.cr.dbname,
        'message': message,
        'func': function_name,
        'path': path,
        'line': '0',
    })

class Listings(models.Model):
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _name = "ebay_listing"
    _description = "ebay_listing model"

    ebay_title = fields.Char('Title', size=80,
                             help='The title is restricted to 80 characters', required=True)
    ebay_URL = fields.Html('URL', default='<p><br></p>')
    ebay_listing_image = fields.Image("Listing Image",attachment = True)
    ebay_category_id = fields.Many2one('ebay.category',
                                       string="Category",
                                       domain=[('category_type', '=', 'ebay'), ('leaf_category', '=', True)], required=True)

    ebay_ePID = fields.Char("ePID", size=13)
    ebay_ISBN = fields.Char("ISBN", size = 13)
    ebay_EAN = fields.Char("EAN", size=13)
    ebay_UPC = fields.Char("UPC", size=13)


    # ebay_current_price = fields.Float('Current Price', readonly =True)
    ebay_suggesting_price = fields.Float('Suggested', readonly =True)
    ebay_competition_price = fields.Float('My Competition', readonly =True)
    ebay_s_competitor = fields.Float("Super Competitor", readonly =True)
    ebay_min_price = fields.Float('Minimum', required=True)
    ebay_max_price = fields.Float('Maximum', required=True)

    # ebay_automated_accepting = fields.Boolean("Automated Accepting", default = True)
    ebay_automated_suggesting = fields.Boolean("Automated Suggesting", default = True)
    ebay_interval_type = fields.Selection([
        ('day', 'Every Day'),
        ('hour', 'Every Hour'),
        ('30m', 'Every Half Hour'),
        ('custom', 'Custom')
    ], string='Interval Type', default='hour', required=True)
    ebay_interval_value = fields.Char("Interval Value", help="Interval Format e.g :'1h 30m'", default ="45m")

    interval_number = fields.Integer("Interval", compute='_period_in_minutes' )
    ebay_next_call = fields.Datetime("Next call")

    ebay_search_strategy = fields.Selection([
        ('keyword', 'Keyword'),
        ('productId', 'Product ID')
        ], string='Search Strategy', default='keyword', required=True)
    
    def _default_keyword(self):
        for rec in self:
            print("123123123")
            res = rec.ebay_title
            print(res)
            return res
    ebay_keyword = fields.Text("Keyword")
    ebay_instock = fields.Integer("In stock")

    itemIDs = fields.One2many("ebay_listing.item", "listId", readonly =True )    # , readonly =True
    ebay_repricer = fields.Many2one("ebay_suggesting_rules","Repricing Rules")
    competitionIDs = fields.One2many("competitions", "listingID", readonly =True )    # , readonly =True
    competition_count = fields.Integer(string='Competition Count', compute='_get_competition_count', readonly=True)

    # currency_id = fields.Many2one('res.currency', 'Currency',
    #                               default=lambda self: self.env.user.company_id.currency_id, required=True)
    # currency_id = fields.Many2one('res.currency', 'Currency',
    #                               default=2, required=True)

    ebay_automated_rouding = fields.Boolean("Automated Rounding", default=True)
    ebay_rouding_strategy = fields.Selection([
        ('9', 'Price Nearest 9'),
        ('.99', 'Price Nearest .99'),
        ('.49', 'Price Nearest .49')
    ], string='Rouding Strategy', default='.99', required=True)

    ################################################################################################
    ################### Functions ##################################################################
    ################################################################################################
    ################ Compute #######################################################################
    
    def _period_in_minutes(self):
        for record in self:
            if record.ebay_interval_type == 'day':
                record.interval_number = 24 * 60
            elif record.ebay_interval_type == 'hour':
                record.interval_number = 60
            elif record.ebay_interval_type == '30m':
                record.interval_number = 30
            else:
                interval_value_component = record.ebay_interval_value.split()
                if len(interval_value_component) == 2:
                    record.interval_number = int(interval_value_component[0][:-1]) * 60 + int(interval_value_component[1][:-1])
                else:
                    record.interval_number = int(interval_value_component[0][:-1]) * 60 if interval_value_component[0][-1] == 'h' else int(interval_value_component[0][:-1])
    def _get_competition_count(self):
        for record in self:
            record.competition_count = self.env['competitions'].search_count([
            ['listingID', '=', record.id]
        ])
    ################ Onchange #######################################################################

    @api.onchange('ebay_automated_suggesting')
    def _compute_next_call(self):
        for record in self:
            if record.ebay_automated_suggesting:
                record.ebay_next_call = datetime.now() + relativedelta(minutes = record.interval_number)
    @api.onchange('ebay_keyword')
    def _check_valid_keyword(self):
        for record in self:
            if record.ebay_keyword == '':
                record.ebay_keyword = record.ebay_title

    @api.onchange('ebay_interval_type')
    def _compute_next_call_by_interval_type(self):
        for record in self:
            if record.ebay_automated_suggesting:
                record.ebay_next_call = datetime.now() + relativedelta(minutes=record.interval_number)

    @api.onchange('ebay_interval_value')
    def _compute_next_call_by_interval_number(self):
        for record in self:
            print("change interval")
            if record.ebay_automated_suggesting:
                print(record.interval_number)
                record.ebay_next_call = datetime.now() + relativedelta(minutes=record.interval_number)
                print(record.ebay_next_call)
    @api.onchange('ebay_next_call')
    def _check_valid_next_call(self):
        for record in self:
            print("change next call")
            now = datetime.now()
            if now >= record.ebay_next_call:
                raise ValidationError("Next call value invalid!")
    ################ Constraints #######################################################################

    @api.constrains('ebay_min_price')
    def _check_negative_min_price(self):
        for record in self:
            if record.ebay_min_price < 0:
                raise ValidationError("Min price cannot be negative")

    @api.constrains('ebay_max_price')
    def _check_negative_max_price(self):
        for record in self:
            if record.ebay_max_price < 0:
                raise ValidationError("Max price cannot be negative")

    @api.constrains('ebay_instock')
    def _check_negative_instock(self):
        for record in self:
            if record.ebay_instock < 0:
                raise ValidationError("Instock cannot be negative")

    @api.constrains('ebay_min_price', 'ebay_max_price')
    def _check_min_max_price(self):
        for record in self:
            if record.ebay_min_price > record.ebay_max_price:
                raise ValidationError("Min price must be smaller than Max price")

    @api.constrains('ebay_interval_value')
    def _check_interval_format(self):
        for record in self:
            interval_component = record.ebay_interval_value.split()
            if len(interval_component) >= 3:
                raise ValidationError("Interval format e.g: '1h 30m'")
            elif len(interval_component) == 2:
                if interval_component[0][-1] != 'h' or interval_component[1][-1] != 'm':            # if != 'h' or 'm' 
                    raise ValidationError("Interval format e.g: '1h 30m'")
                for lit in interval_component[0][:-1]:                                              # check literal type first index
                    if lit not in ['0','1','2','3','4','5','6','7','8','9']:
                        raise ValidationError("Hour value invalid, must be integer, Interval format e.g: '1h 30m'")
                if int(interval_component[0][:-1]) < 0 and int(interval_component[0][:-1]) > 23:    # negative value hour
                    raise ValidationError("Hour value invalid!")
                for lit in interval_component[1][:-1]:                                              # check literal type second index
                    if lit not in ['0','1','2','3','4','5','6','7','8','9']:
                        raise ValidationError("Minute value invalid, must be integer, Interval format e.g: '1h 30m'")
                if int(interval_component[1][:-1]) < 0 and int(interval_component[1][:-1]) > 59:    # negative value minute
                    raise ValidationError("Minute value invalid")
                if int(interval_component[0][:-1]) == 0 and int(interval_component[1][:-1]) < 30:
                    raise ValidationError("Min Interval value at least 30 minutes!")
            else:
                if interval_component[0][-1] not in ['h','m']:                                      # minute or hour
                    raise ValidationError("Wrong interval format, e.g: '30m' or '2h'")
                for lit in interval_component[0][:-1]:
                    if lit not in ['0','1','2','3','4','5','6','7','8','9']:
                        raise ValidationError("Invalid value, Interval format e.g: '30m' or '2h'")
                if interval_component[0][-1] == 'm':
                    if int(interval_component[0][:-1]) < 30:
                        raise ValidationError("Min Interval value at least 30 minutes!")


    

    def name_get(self):
        result = []
        for rec in self:
            name = "L" + str(rec.id).zfill(5)
            result.append((rec.id, name))
        return result
    ### override
    # @api.model
    # def write(self, vals):
    #     res = super(Listings, self).write(vals)

    ################ Actions #######################################################################

    # def action_accept_suggesting_price(self):
    #     for rec in self:
    #         rec.write({
    #             "ebay_current_price":rec.ebay_suggesting_price,
    #         })
    #         rec.itemIDs += self.env['ebay_listing.item'].create({
    #             'price': rec.ebay_suggesting_price,
    #             'current_price': rec.ebay_current_price,
    #             's_competitor': rec.ebay_s_competitor
    #         })
    def build_request(self,rec):
        request = {}
        if rec.ebay_search_strategy == 'keyword':
            if rec.ebay_keyword:
                request['keywords'] = rec.ebay_keyword
            else:
                raise ValidationError("Keyword must be empty!")
            request['categoryId'] = rec.ebay_category_id.category_id
        else:
            if rec.ebay_ISBN:
                type_value = 'ISBN'
                text_value = rec.ebay_ISBN
            elif rec.ebay_UPC:
                type_value = 'UPC'
                text_value = rec.ebay_UPC
            elif rec.ebay_EAN:
                type_value = 'EAN'
                text_value = rec.ebay_EAN
            elif rec.ebay_ePID:
                type_value = 'ePID'
                text_value = rec.ebay_ePID
            else:
                raise ValidationError("ProductID is empty!")

            request['productId'] = {
                '#text': text_value,
                '@attrs': {
                    'type': type_value
                }
            }
        if not request:
            raise ValidationError("Request is empty!")

        request['itemFilter'] = [
            {'name': 'ListingType', 'value': 'FixedPrice'},
            {'name': 'Condition', 'value': 'New', },
        ]
        request['paginationInput'] = {
            'entriesPerPage': 50,
            'pageNumber': 1
        }
        request['sortOrder'] = 'PricePlusShippingLowest'
        request['outputSelector'] = 'SellerInfo'
        print(request)
        return request

    def compute_suggesting_price(self, rec, my_competitor):

        if isinstance(rec.ebay_repricer.rname,bool):
            raise ValidationError("Please choose the rule!")

        rules = rec.ebay_repricer.rname.split()  # rules format e.g ['Above', '$1.5'] or ['Below', '5%'] or ['Matching']

        if rules[0] == 'Matching':
            return str(my_competitor)
        else:
            if rules[0] == 'Below':
                my_competitor -= float(rules[1][1:]) if rules[1][0] == '$' else my_competitor * float(rules[1][:-1]) / 100.00
            else:
                my_competitor += float(rules[1][1:]) if rules[1][0] == '$' else my_competitor * float(rules[1][-1]) / 100.00
            if rec.ebay_automated_rouding:
                if rec.ebay_rouding_strategy == '9':
                    my_competitor = int(my_competitor/10)*10 + 9
                elif rec.ebay_rouding_strategy == '.99':
                    my_competitor = int(my_competitor) + 0.99
                else:
                    my_competitor = int(my_competitor) + 0.49
            else:
                my_competitor = round(my_competitor,2)
            return str(my_competitor)
    def _create_competitions_db(self, rec, listing):

        rec.competitionIDs += self.env['competitions'].create({
            'title':    listing.title,
            'URL':      listing.viewItemURL,
            'sellerUserName':   listing.sellerInfo.sellerUserName,
            'positiveFeedbackPercent': listing.sellerInfo.positiveFeedbackPercent,
            'topRatedSeller':   True if listing.sellerInfo.topRatedSeller == 'true' else False,
            'current_price':    listing.sellingStatus.currentPrice.value,
            'shippingType':     listing.shippingInfo.shippingType,
            'shippingServiceCost': listing.shippingInfo.shippingServiceCost.value if listing.shippingInfo.get('shippingServiceCost') else 'inf',
            'total_cost': str(round(float(listing.sellingStatus.currentPrice.value) + float(listing.shippingInfo.shippingServiceCost.value),2)) if listing.shippingInfo.get('shippingServiceCost') else 'inf'
        })
    def _action_suggesting_price(self,rec):
        request = self.build_request(rec)
        try:
            ebay_api = Finding(
                domain='svcs.ebay.com',
                config_file=None,
                appid= self.env['ir.config_parameter'].sudo().get_param('ebay_prod_app_id'),
                siteid=self.env['ebay.site'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('ebay_site')))], limit=1).name.split()[0],
                https=True,
            )
            time.sleep(0.01)
        except ConnectionError as e:
            print(e)
            print(e.response.dict())
        if rec.ebay_search_strategy == 'keyword':
            response = ebay_api.execute('findItemsAdvanced', request)
        else:
            response = ebay_api.execute('findItemsByProduct', request)


        if response.reply.ack == 'Success':
            super_competition_price = float('inf')                              # set super price = inf
            if response.reply.searchResult._count == '0':                       # check list of result, if result is empty, _count = '0'
                raise ValidationError("Not found Items!!")                      # raise Error
            isCalculated = True
            for listing in response.reply.searchResult.item:                    # handle suggested price
                if listing.shippingInfo.get('shippingServiceCost'):             # if shippingServiceCost is exist
                    my_competitor = float(listing.sellingStatus.currentPrice.value) + float(
                        listing.shippingInfo.shippingServiceCost.value)
                    super_competition_price = my_competitor if my_competitor < super_competition_price else super_competition_price

                    isCalculated = False

                    if my_competitor < rec.ebay_min_price:
                        continue
                    elif my_competitor >= rec.ebay_min_price and my_competitor <= rec.ebay_max_price:
                        suggesting_price = self.compute_suggesting_price(rec, my_competitor)
                        # print(suggesting_price)
                        # print(rec.ebay_min_price)
                        # print(rec.ebay_min_price)
                        if float(suggesting_price) >= rec.ebay_min_price and float(
                                suggesting_price) <= rec.ebay_max_price:    # suggesting price in [min.max]
                            rec.ebay_suggesting_price = suggesting_price    # update suggesting price
                        else:
                            suggesting_price = rec.ebay_min_price
                            rec.ebay_suggesting_price = suggesting_price
                        rec.ebay_s_competitor = super_competition_price     #   update super competition price
                        rec.ebay_competition_price = my_competitor          #   update competition price
                        # if rec.ebay_automated_accepting:
                        #     rec.ebay_current_price = suggesting_price       #   update automated current price
                        rec.ebay_next_call = datetime.now() + relativedelta(minutes=rec.interval_number)    # update next call
                        rec.itemIDs += self.env['ebay_listing.item'].create({
                            'price': suggesting_price,
                            #'current_price': rec.ebay_current_price,  # update in the future
                            's_competitor': super_competition_price,
                            'min_price' : rec.ebay_min_price,
                            'max_price' : rec.ebay_max_price,
                            'search_type': dict(rec._fields['ebay_search_strategy'].selection).get(rec.ebay_search_strategy)
                        })
                        break
                    else:
                        rec.ebay_next_call += relativedelta(minutes=rec.interval_number)  # update next call
                        break


                else:
                    pass
                    # my_competitor = float('-inf')
                    #my_competitor = float(listing.sellingStatus.currentPrice.value) # shippingType Calculated

                
            if isCalculated:
                for listing in response.reply.searchResult.item:
                    my_competitor = float(listing.sellingStatus.currentPrice.value) # shippingType Calculated
                    super_competition_price = my_competitor if my_competitor < super_competition_price else super_competition_price

                    if my_competitor < rec.ebay_min_price:
                        continue
                    elif my_competitor >= rec.ebay_min_price and my_competitor <= rec.ebay_max_price:
                        suggesting_price = self.compute_suggesting_price(rec, my_competitor)
                        # print(suggesting_price)
                        # print(rec.ebay_min_price)
                        # print(rec.ebay_min_price)
                        if float(suggesting_price) >= rec.ebay_min_price and float(
                                suggesting_price) <= rec.ebay_max_price:    # suggesting price in [min.max]
                            rec.ebay_suggesting_price = suggesting_price    # update suggesting price
                        else:
                            suggesting_price = rec.ebay_min_price
                            rec.ebay_suggesting_price = suggesting_price
                        rec.ebay_s_competitor = super_competition_price     #   update super competition price
                        rec.ebay_competition_price = my_competitor          #   update competition price
                        # if rec.ebay_automated_accepting:
                        #     rec.ebay_current_price = suggesting_price       #   update automated current price
                        rec.ebay_next_call = datetime.now() + relativedelta(minutes=rec.interval_number)    # update next call
                        rec.itemIDs += self.env['ebay_listing.item'].create({
                            'price': suggesting_price,
                            #'current_price': rec.ebay_current_price,  # update in the future
                            's_competitor': super_competition_price
                        })
                        break
                    else:
                        rec.ebay_next_call += relativedelta(minutes=rec.interval_number)  # update next call
                        break
            self.env.cr.execute("""
                DELETE FROM public.competitions
	                WHERE "listingID" = %s;
            """, [rec.id])
            for listing in response.reply.searchResult.item:
                self._create_competitions_db(rec, listing)
        elif response.reply.ack == 'Failure':
            raise ValidationError(response.reply.errorMessage.error.message)
        else:
            raise ValidationError("Something went wrong!!")

    def action_suggesting_price(self):
        for rec in self:
            self._action_suggesting_price(rec)
    def automated_suggesting_price(self):
        listings = self.env['ebay_listing'].search([])
        for listing in listings:
            if listing.ebay_automated_suggesting:
                now = datetime.now()
                if now >= listing.ebay_next_call:
                    self._action_suggesting_price(listing)
    
    
    def action_view_competition(self):
        return{
            'name': 'Competitions',
            'view_mode': 'tree',
            'res_model': 'competitions',
            'type': 'ir.actions.act_window',
            'domain': [('listingID','=',self.id)]
        }
    def action_graph_view(self):
        return {
            'name': 'Graph',
            'view_mode': 'graph',
            'res_model': 'ebay_listing.item',
            'type': 'ir.actions.act_window',
            'domain': [('listId', '=', self.id)]
        }
    
    @api.model
    def create(self, vals):
        vals['ebay_keyword'] = vals['ebay_title']
        rec = super(Listings, self).create(vals)      
        return rec


class ListingItems(models.Model):
    #_inherit = "product.template"
    _name = "ebay_listing.item"
    _description = "ebay_listing_item model"
    _order = "create_date desc"

    listId = fields.Many2one("ebay_listing", "Listing Id", ondelete='cascade' )
    price = fields.Float("Suggesting Price" )
    # current_price = fields.Float("Current Price")
    s_competitor = fields.Float("Super Competitor")
    min_price = fields.Float("Min Price")
    max_price = fields.Float("Max Price")
    search_type = fields.Char("Search Strategy")
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=2, required=True)
