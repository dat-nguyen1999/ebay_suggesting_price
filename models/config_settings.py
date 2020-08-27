from odoo import api, fields, models
from tools.ebaysdk import Finding


class ConfigSettings(models.Model):
    _inherit = 'res.config.settings'
    _name    = 'ebay_config_settings'
    _description = 'eBay ConfigSettings'

    ebay_app_id = fields.Char("App Key", default='', config_parameter='ebay_app_id')

    def set_values(self):
        super(ConfigSettings, self).set_values()
        set_param = self.env['ir.config.parameter'].sudo().set_param

        ebay_api = Finding(
            config_file=None,
            app_id = self.ebay_app_id
        )