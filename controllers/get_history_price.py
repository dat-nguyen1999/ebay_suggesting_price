import odoo
import logging
import json
import datetime
_logger = logging.getLogger(__name__)

class GetHistoryPriceAPI(odoo.http.Controller):

    @odoo.http.route(['/info/ebay_listing_item/<id>'], type='http', methods=['GET'], auth="user", csrf=False)
    def get_by_listingID(self, id, **kw):
        model_name = "ebay_listing.item"
        try:
            history_price = odoo.http.request.env[model_name].search(
                [
                    ('listId', '=', int(id)),
                    ('create_date', '>=', datetime.datetime.now() - datetime.timedelta(days=7))
                ],
                limit=60)
            labels = []
            suggesting_price = []
            super_competition = []
            for rec in history_price:
                labels.insert(0, str((rec.create_date + datetime.timedelta(hours=7)).strftime("%Y-%m-%d, %H:%M")))
                suggesting_price.insert(0, rec.price)
                super_competition.insert(0, rec.s_competitor)

            response = {
                "label": labels,
                "suggesting": suggesting_price,
                "super_competition": super_competition

            }
        except Exception:
            response = {
                "status": "error",
                "content": "not found"
            }

        return json.dumps(response)