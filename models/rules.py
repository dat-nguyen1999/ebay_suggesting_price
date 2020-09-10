from odoo import models, fields, api
from odoo.exceptions import UserError, RedirectWarning, ValidationError
# class Suggesting_Rules(models.Model):
#     _name = "ebay_suggesting_rules"
#     _description = "suggesting rules model"
#     ebay_rule_type = fields.Selection([
#         ('no_competitor', 'No Competitor'),
#         ('upon_competitor', 'Fixed price')], string='Rule Type', default='upon_competitor')
#     ebay_interval = fields.Datetime("Schedule Pricing")
#     ebay_rule_name = fields.Char("Rule Name")
#
# class No_Competitors(models.Model):
#     _inherit = "ebay_suggesting_rules"
#     _name = "ebay_suggesting_rules.no_competitors"
#     _description = "suggesting rules if no competitors"
#     ebay_suggesting_strategy = fields.Selection([
#         ('min', 'Set Minimum Price'),
#         ('max', 'Set Maximum Price'),
#         ('nochange', 'Do not suggest')], string='Suggesting Strategy', default='nochange')
#     @api.depends('ebay_suggesting_strategy')
#     def set_ebay_rule_name(self):
#         self.ebay_rule_name = self.ebay_suggesting_strategy
#
# class Upon_Competitors(models.Model):
#     _inherit = "ebay_suggesting_rules"
#     _name = "ebay_suggesting_rules.upon_competitors"
#     _description = "suggesting rules if upon competitors"
#     ebay_suggesting_strategy = fields.Selection([
#         ('matching', 'Matching'),
#         ('below', 'Below'),
#         ('above', 'Above'),], string='Suggesting Strategy', default='matching')
#     ebay_amount_type = fields.Selection([
#         ('percentage','Percentage'),
#         ('dollar','Dollar')], string='Amount Type', default='dollar')
#     ebay_amount_value = fields.Float('Amount value', required = True)
#     ebay_top_rate_option = fields.Boolean("Top rate option")
class Suggesting_Rules(models.Model):
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _name = "ebay_suggesting_rules"
    _description = "suggesting rules model"
    _rec_name = 'rname'
    rname = fields.Char("Rule Name", compute='_set_ebay_rule_name', copy=False)

    ebay_suggesting_strategy = fields.Selection([
        ('matching', 'Matching'),
        ('below', 'Below'),
        ('above', 'Above'),], string='Suggesting Strategy', default='below')
    ebay_amount_type = fields.Selection([
        ('%','%'),
        ('$','$')], string='Amount Type', default='$')
    ebay_amount_value = fields.Float('Amount value')
    ebay_top_rate_option = fields.Boolean("Top rate option")

    ebay_listings = fields.One2many("ebay_listing", "ebay_repricer")


    #### Constraints######
    @api.constrains('ebay_amount_value')
    def _check_negative_amount_value(self):
        for record in self:
            if record.ebay_amount_value < 0:
                raise ValidationError("Amount value cannot be negative")


    @api.depends('ebay_suggesting_strategy','ebay_amount_type','ebay_amount_value')
    def _set_ebay_rule_name(self):
        for rec in self:
            # count = self.env['ebay_suggesting_rules'].search_count([
            #     ['ebay_suggesting_strategy', '=', rec.ebay_suggesting_strategy],
            #     ['ebay_amount_value', '=', rec.ebay_amount_value],
            #     ['ebay_amount_type', '=', rec.ebay_amount_type]
            # ])
            # print(count)
            # if count != 1:
            #     raise ValidationError("Rules has existed !")
            if rec.ebay_suggesting_strategy != 'matching':
                rec.rname = dict(rec._fields['ebay_suggesting_strategy'].selection).get(rec.ebay_suggesting_strategy) + ' ' + str(rec.ebay_amount_value) + ' ' + dict(rec._fields['ebay_amount_type'].selection).get(rec.ebay_amount_type)
            else:
                rec.rname = dict(rec._fields['ebay_suggesting_strategy'].selection).get(rec.ebay_suggesting_strategy)

    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         name = rec.rname + " ID_" + str(rec.id)
    #         result.append((rec.id, name))
    #     return result

    @api.model
    def create(self, vals):
        query = self.env['ebay_suggesting_rules'].search_count([
            ['ebay_suggesting_strategy', '=', vals.get('ebay_suggesting_strategy')],
            ['ebay_amount_value', '=', vals.get('ebay_amount_value')],
            ['ebay_amount_type', '=', vals.get('ebay_amount_type')]
        ])
        if query:
            raise ValidationError("Rules has existed !")
        rec = super(Suggesting_Rules, self).create(vals)      
        return rec
    
    @api.model
    def write(self, args ,vals):
        print(vals)
        print(args)
        try:
            rec_id = args[0]
        except TypeError as e:
            raise('Something went wrong')
        rec = self.browse(rec_id)
        ebay_suggesting_strategy = vals.get('ebay_suggesting_strategy') if 'ebay_suggesting_strategy' in vals else rec.ebay_suggesting_strategy
        ebay_amount_value =  vals.get('ebay_amount_value') if 'ebay_amount_value' in vals else rec.ebay_amount_value
        ebay_amount_type =  vals.get('ebay_amount_type') if 'ebay_amount_type' in vals else rec.ebay_amount_type
        query = self.env['ebay_suggesting_rules'].search_count([
            ['ebay_suggesting_strategy', '=', ebay_suggesting_strategy],
            ['ebay_amount_value', '=', ebay_amount_value],
            ['ebay_amount_type', '=', ebay_amount_type]
        ])
        if query:
            raise ValidationError("Rules has existed !")
        rec = super(Suggesting_Rules, self).write(vals)      
        return rec