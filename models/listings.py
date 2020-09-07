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

    itemId = fields.Char("ItemID",required=True, copy=False)  #readonly = True
    ebay_title = fields.Char('Title', size=80,
                             help='The title is restricted to 80 characters', required=True)
    ebay_URL = fields.Html('URL', default='<p><br></p>')
    ebay_listing_image = fields.Image("Listing Image",attachment = True)
    ebay_category_id = fields.Many2one('ebay.category',
                                       string="Category",
                                       domain=[('category_type', '=', 'ebay'), ('leaf_category', '=', True)], required=True)
    #ebay_listing_type = fields.Char("Listing Type", required=True)
    # ebay_listing_type = fields.Selection([
    #             #('Chinese', 'Auction'),
    #             ('FixedPriceItem', 'Fixed price')], string='Listing Type', default='FixedPriceItem')
    ebay_ePID = fields.Char("ePID", size=13)
    ebay_ISBN = fields.Char("ISBN", size = 13)
    ebay_EAN = fields.Char("EAN", size=13)
    ebay_UPC = fields.Char("UPC", size=13)


    ebay_current_price = fields.Float('Current Price', readonly =True)
    ebay_suggesting_price = fields.Float('Suggesting Price', readonly =True)
    ebay_competition_price = fields.Float('Competition Price', readonly =True)
    ebay_s_competitor = fields.Float("Super Competitor", readonly =True)
    ebay_min_price = fields.Float('Minimum Price', required=True)
    ebay_max_price = fields.Float('Maximum Price', required=True)

    ebay_automated_accepting = fields.Boolean("Automated Accepting", default = True)
    ebay_automated_suggesting = fields.Boolean("Automated Suggesting", default = True)
    ebay_interval_type = fields.Selection([
        ('daily', 'Daily'),
        ('hourly', 'Hourly'),
        ('minutely', 'Minutely'),
        ('custom', 'Custom')
    ], string='Interval Type', default='hourly', required=True)
    ebay_interval_value = fields.Char("Interval Value", help="Interval Format e.g :'1h 30m'", default ="45m")

    interval_number = fields.Integer("Interval", compute='_period_in_minutes' )
    ebay_next_call = fields.Datetime("Next call", readonly =True)

    ebay_search_strategy = fields.Selection([
        ('keyword', 'Keyword'),
        ('barcode', 'Barcode')
        ], string='Search Strategy', default='keyword', required=True)
    ebay_keyword = fields.Text("Keyword")
    ebay_instock = fields.Integer("In stock")

    itemIDs = fields.One2many("ebay_listing.item", "listId", readonly =True )    # , readonly =True
    ebay_repricer = fields.Many2one("ebay_suggesting_rules","Repricing Rules")


    ################################################################################################
    ################### Functions ##################################################################
    ################################################################################################
    ################ Compute #######################################################################
    def _period_in_minutes(self):
        for record in self:
            if record.ebay_interval_type == 'daily':
                record.interval_number = 24 * 60
            elif record.ebay_interval_type == 'hourly':
                record.interval_number = 60
            elif record.ebay_interval_type == 'minutely':
                record.interval_number = 1
            else:
                interval_value_component = record.ebay_interval_value.split()
                if len(interval_value_component) == 2:
                    record.interval_number = int(interval_value_component[0][:-1]) * 60 + int(interval_value_component[1][:-1])
                else:
                    record.interval_number = int(interval_value_component[0][:-1]) * 60 if interval_value_component[0][-1] == 'h' else int(interval_value_component[0][:-1])

    ################ Onchange #######################################################################

    @api.onchange('ebay_automated_suggesting')
    def _compute_next_call(self):
        for record in self:
            if record.ebay_automated_suggesting:
                record.ebay_next_call = datetime.now() + relativedelta(minutes = record.interval_number)

    @api.onchange('ebay_interval_type')
    def _compute_next_call_by_interval_type(self):
        for record in self:
            if record.ebay_automated_suggesting:
                record.ebay_next_call = datetime.now() + relativedelta(minutes=record.interval_number)

    @api.onchange('interval_number')
    def _compute_next_call_by_interval_number(self):
        for record in self:
            if record.ebay_automated_suggesting:
                record.ebay_next_call = datetime.now() + relativedelta(minutes=record.interval_number)

    ################ Constraints #######################################################################

    @api.constrains('itemId')
    def _check_itemId_unique(self):
        dict_itemId = { }
        for record in self:
            if dict_itemId.get(record.itemId):
                raise ValidationError("Fields itemId already exists!")
            dict_itemId[record.itemId] = True

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
                if interval_component[0][-1] != 'h' or interval_component[1][-1] != 'm':
                    raise ValidationError("Interval format e.g: '1h 30m'")
                for lit in interval_component[0][:-1]:
                    if lit not in ['0','1','2','3','4','5','6','7','8','9']:
                        raise ValidationError("Interval format e.g: '1h 30m'")
                if int(interval_component[0][:-1]) < 0 and int(interval_component[0][:-1]) > 23:
                    raise ValidationError("Interval format e.g: '1h 30m'")
                for lit in interval_component[1][:-1]:
                    if lit not in ['0','1','2','3','4','5','6','7','8','9']:
                        raise ValidationError("Interval format e.g: '1h 30m'")
                if int(interval_component[1][:-1]) < 0 and int(interval_component[1][:-1]) > 59:
                    raise ValidationError("Interval format e.g: '1h 30m'")
            else:
                if interval_component[0][-1] not in ['h','m']:
                    raise ValidationError("Interval format e.g: '30m' or '2h'")
                for lit in interval_component[0][:-1]:
                    if lit not in ['0','1','2','3','4','5','6','7','8','9']:
                        raise ValidationError("Interval format e.g: '30m' or '2h'")
    # @api.depends('ebay_ePID', 'ebay_ISBN','ebay_EAN', 'ebay_UPC')
    # def _check_selection_search_strategy(self):
    #     for record in self:
    #         if record.ebay_ePID or record.ebay_ISBN or record.ebay_EAN or record.ebay_UPC:
    #             record.ebay_search_strategy = fields.Selection( selection_add = [
    #                 ('barcode','Barcode')
    #             ])
    # @api.constrains('ebay_search_strategy', 'ebay_keyword')
    # def _check_keyword(self):
    #     for record in self:
    #         if record.ebay_search_strategy == 'keyword':
    #             raise ValidationError("Keyword must not empty!")


    _sql_constraints = [
        ('itemId_unique', 'unique(itemId)', "itemId already exists!")
    ]

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.itemId))
        return result

    ### override
    # @api.model
    # def write(self, vals):
    #     res = super(Listings, self).write(vals)

    ################ Actions #######################################################################

    def action_accept_suggesting_price(self):
        for rec in self:
            rec.write({
                "ebay_current_price":rec.ebay_suggesting_price,
            })
            rec.itemIDs += self.env['ebay_listing.item'].create({
                'price': rec.ebay_suggesting_price,
                'current_price': rec.ebay_current_price,
                's_competitor': rec.ebay_s_competitor
            })
    def build_request(self,rec):
        request = {}
        if rec.ebay_search_strategy == 'keyword':
            if rec.ebay_keyword:
                request['keywords'] = rec.ebay_keyword
            else:
                raise ValueError("Keyword must be empty!")
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
                raise ValidationError("Barcode is empty!")

            request['productId'] = {
                '#text': text_value,
                '@attrs': {
                    'type': type_value
                }
            }
        if not request:
            raise ValueError("Request is empty!")

        request['itemFilter'] = [
            {'name': 'ListingType', 'value': 'FixedPrice'},
            {'name': 'Condition', 'value': 'New', },
        ]
        request['paginationInput'] = {
            'entriesPerPage': 50,
            'pageNumber': 1
        }
        request['sortOrder'] = 'PricePlusShippingLowest'
        return request

    def compute_suggesting_price(self, rec, my_competitor):
        try:
            rules = rec.ebay_repricer.rname.split()     # rules format e.g ['Above', '1.5', '$']
        except AttributeError as e:
            print(e)

        if rules[0] == 'Matching':
            return str(my_competitor)
        else:
            if rules[0] == 'Below':
                my_competitor -= float(rules[1]) if rules[2] == '$' else my_competitor * float(rules[1]) / 100.00
            else:
                my_competitor += float(rules[1]) if rules[2] == '$' else my_competitor * float(rules[1]) / 100.00
            my_competitor = round(my_competitor,2)
            return str(my_competitor)

    def _action_suggesting_price(self,rec):
        request = self.build_request(rec)
        try:
            print(
                  self.env['ebay.site'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('ebay_site')))], limit=1).name.split()[0])
            ebay_api = Finding(
                domain='svcs.ebay.com',
                config_file=None,
                # appid='DatNguye-simpleca-PRD-0c8ee5576-eb7ef499',
                appid= self.env['ir.config_parameter'].sudo().get_param('ebay_prod_app_id'),
                siteid=self.env['ebay.site'].search([('id', '=', int(self.env['ir.config_parameter'].sudo().get_param('ebay_site')))], limit=1).name.split()[0],
                https=True,
            )
            time.sleep(1)
        except ConnectionError as e:
            print(e)
            print(e.response.dict())
        if rec.ebay_search_strategy == 'keyword':
            response = ebay_api.execute('findItemsAdvanced', request)
        else:
            response = ebay_api.execute('findItemsByProduct', request)

        print(request)

        if response.reply.ack == 'Success':
            super_competition_price = float('inf')
            for listing in response.reply.searchResult.item:
                if listing.shippingInfo.get('shippingServiceCost'):
                    my_competitor = float(listing.sellingStatus.currentPrice.value) + float(
                        listing.shippingInfo.shippingServiceCost.value)
                else:
                    my_competitor = float(listing.sellingStatus.currentPrice.value)
                super_competition_price = my_competitor if my_competitor < super_competition_price else super_competition_price
                print(my_competitor)

                if my_competitor < rec.ebay_min_price:
                    continue
                elif my_competitor >= rec.ebay_min_price and my_competitor <= rec.ebay_max_price:
                    suggesting_price = self.compute_suggesting_price(rec, my_competitor)
                    if float(suggesting_price) >= rec.ebay_min_price and float(
                            suggesting_price) <= rec.ebay_max_price:    # suggesting price in [min.max]
                        rec.ebay_suggesting_price = suggesting_price    # update suggesting price
                    rec.ebay_s_competitor = super_competition_price     #   update super competition price
                    rec.ebay_competition_price = my_competitor          #   update competition price
                    if rec.ebay_automated_accepting:
                        rec.ebay_current_price = suggesting_price       #   update automated current price
                    rec.ebay_next_call = datetime.now() + relativedelta(minutes=rec.interval_number)    # update next call
                    rec.itemIDs += self.env['ebay_listing.item'].create({
                        'price': suggesting_price,
                        'current_price': rec.ebay_current_price,  # update in the future
                        's_competitor': super_competition_price
                    })
                    break
                else:
                    rec.ebay_next_call += relativedelta(minutes=rec.interval_number)  # update next call
                    break
        elif response.reply.ack == 'Failure':
            raise ValidationError(response.reply.errorMessage.error.message)
        else:
            raise ValidationError("Something went wrong!!")

    def action_suggesting_price(self):
        for rec in self:
            self._action_suggesting_price(rec)
    def automated_suggesting_price(self):
        print("Automated!!")
        listings = self.env['ebay_listing'].search([])
        for listing in listings:
            print(listing.ebay_automated_suggesting)
            if listing.ebay_automated_suggesting:
                now = datetime.now()
                if now >= listing.ebay_next_call:
                    self._action_suggesting_price(listing)
                print(listing.ebay_next_call)
                print(listing.interval_number)



class ListingItems(models.Model):
    #_inherit = "product.template"
    _name = "ebay_listing.item"
    _description = "ebay_listing_item model"
    _order = "create_date desc"

    listId = fields.Many2one("ebay_listing", "Listing Id", ondelete='cascade' )
    price = fields.Float("Suggesting Price" )
    current_price = fields.Float("Current Price")
    s_competitor = fields.Float("Super Competitor")

