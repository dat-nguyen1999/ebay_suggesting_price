import odoo
import logging
import json
import datetime
_logger = logging.getLogger(__name__)

class GetHistoryPriceAPI(odoo.http.Controller):

    @odoo.http.route(['/info/ebay_listing_item/<id>'], type='http', methods=['GET'], auth="user", csrf=False)
    def get_by_listingID(self, id, group_by='day'):
        model_name = "ebay_listing.item"
        try:
            labels = []
            suggesting_price = []
            super_competition = []
            minimum_price = []
            maximum_price = []
            if group_by == 'day':
                history_price = odoo.http.request.env[model_name].search(
                    [
                        ('listId', '=', int(id)),
                        ('create_date', '>=', (datetime.datetime.now() - datetime.timedelta(hours=7) ).replace(hour=0, minute=0, second=0, microsecond=0))
                    ],
                )
                print(len(history_price))
                for rec in history_price:
                    if (rec.create_date + datetime.timedelta(hours=7)).date() >= datetime.datetime.now().date():
                        print((rec.create_date + datetime.timedelta(hours=7)).date())
                        labels.insert(0, str((rec.create_date + datetime.timedelta(hours=7)).strftime("%Y-%m-%d %H:%M")))
                        suggesting_price.insert(0, rec.price)
                        super_competition.insert(0, rec.s_competitor)
                        minimum_price.insert(0, rec.min_price)
                        maximum_price.insert(0, rec.max_price)
                    else:
                        break

            elif group_by == 'week':
                thisweek = datetime.datetime.now().isocalendar()[1]
                Convert_Day = {
                    0: 'Monday',
                    1: 'Tuesday',
                    2: 'Wednesday',
                    3: 'Thursday',
                    4: 'Friday',
                    5: 'Saturday',
                    6: 'Sunday'
                }
                for i in range(0,7):
                    history_price = odoo.http.request.env[model_name].search(
                        [
                            ('listId', '=', int(id)),
                            ('create_date', '>=', (datetime.datetime.now() - datetime.timedelta(hours=7)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=i)),
                            ('create_date', '<=', (datetime.datetime.now() - datetime.timedelta(hours=7)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta( days= i - 1 ))
                        ],
                    )
                    print(len(history_price))
                    if len(history_price) == 0:
                        continue
                    sum_suggesting_price = 0
                    sum_super_competition = 0
                    sum_minimum_price = 0
                    sum_maximum_price = 0
                    count = 0
                    for rec in history_price:
                        if (rec.create_date + datetime.timedelta(hours=7)).isocalendar()[1] == thisweek:
                            sum_suggesting_price += rec.price
                            sum_super_competition += rec.s_competitor
                            sum_maximum_price += rec.max_price
                            sum_minimum_price += rec.min_price
                            count += 1
                        else:
                            break

                    if count == 0:
                        continue
                    else:
                        day = (datetime.datetime.now() - datetime.timedelta(days=i)).weekday()

                        labels.insert(0,Convert_Day.get(day))
                        suggesting_price.insert(0, round(float(sum_suggesting_price/count), 2))
                        super_competition.insert(0, round(float(sum_super_competition/count), 2))
                        minimum_price.insert(0, round(float(sum_minimum_price/count), 2))
                        maximum_price.insert(0, round(float(sum_maximum_price/count), 2))
                    # print(Convert_Day.get((datetime.datetime.now() - datetime.timedelta(days=i)).weekday()))

            else:
                thismonth = datetime.datetime.now().month
                for i in range(0, 31):
                    history_price = odoo.http.request.env[model_name].search(
                        [
                            ('listId', '=', int(id)),
                            ('create_date', '>=',
                             (datetime.datetime.now() - datetime.timedelta(hours=7)).replace(hour=0, minute=0, second=0,
                                                                                             microsecond=0) - datetime.timedelta(
                                 days=i)),
                            ('create_date', '<=',
                             (datetime.datetime.now() - datetime.timedelta(hours=7)).replace(hour=0, minute=0, second=0,
                                                                                             microsecond=0) - datetime.timedelta(
                                 days=i - 1))
                        ],
                    )
                    if len(history_price) == 0:
                        continue
                    sum_suggesting_price = 0
                    sum_super_competition = 0
                    sum_minimum_price = 0
                    sum_maximum_price = 0
                    count = 0
                    for rec in history_price:
                        if (rec.create_date + datetime.timedelta(hours=7)).month == thismonth:
                            sum_suggesting_price += rec.price
                            sum_super_competition += rec.s_competitor
                            sum_maximum_price += rec.max_price
                            sum_minimum_price += rec.min_price
                            count += 1
                        else:
                            break

                    if count == 0:
                        continue
                    else:
                        day = (datetime.datetime.now() - datetime.timedelta(days=i))
                        print(day.strftime("%Y-%m-%d"))
                        labels.insert(0, day.strftime("%Y-%m-%d"))
                        suggesting_price.insert(0, round(float(sum_suggesting_price / count), 2))
                        super_competition.insert(0, round(float(sum_super_competition / count), 2))
                        minimum_price.insert(0, round(float(sum_minimum_price / count), 2))
                        maximum_price.insert(0, round(float(sum_maximum_price / count), 2))
                    # print(Convert_Day.get((datetime.datetime.now() - datetime.timedelta(days=i)).weekday()))


            response = {
                "label": labels,
                "suggesting": suggesting_price,
                "super_competition": super_competition,
                "minimum_price": minimum_price,
                "maximum_price": maximum_price

            }
        except Exception:
            response = {
                "status": "error",
                "content": "not found"
            }

        return json.dumps(response)