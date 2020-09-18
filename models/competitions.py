from odoo import models, fields, api
from odoo.exceptions import UserError, RedirectWarning, ValidationError
class Competitions(models.Model):
    #_inherit = ["mail.thread", "mail.activity.mixin"]
    _name = "competitions"
    _description = "list of competitive listing"
    
    
    title = fields.Char("Title")
    URL = fields.Html('URL', default='<p><br></p>')

    sellerUserName = fields.Char("Seller UserName")
    positiveFeedbackPercent = fields.Float("Positive Feedback Percent")
    topRatedSeller = fields.Boolean("Top rated Seller")

    current_price = fields.Char("Current Price")
    shippingType = fields.Char("Shipping Type")
    shippingServiceCost = fields.Char("Shipping Service Cost")
    
    total_cost = fields.Char("Total cost", help="Price Plus Shipping")
    
    listingID = fields.Many2one("ebay_listing", "MyListing")