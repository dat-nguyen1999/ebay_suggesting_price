import odoo
import logging
import json
import datetime
_logger = logging.getLogger(__name__)


class GetHistoryPriceAPI(odoo.http.Controller):

    @odoo.http.route(['/info/ebay_listing_item/<id>'], type='http', methods=['GET'], auth="user", csrf=False)
    def get_by_listingID(self, id, group_by='day'):
        model_name = "ebay_listing.item"

        labels = []
        suggesting_price = []
        super_competition = []
        my_competition = []
        minimum_price = []
        maximum_price = []
        reason = []
        if group_by == 'day':
            current_date = (datetime.datetime.now() + datetime.timedelta(hours=7)).date()
            query = """
                select * from public.ebay_listing_item
                    where "listId" = {} and create_date >=  '{} 17:00:00' and create_date < '{} 17:00:00'
                    order by create_date ASC
                            """.format(id, str(current_date - datetime.timedelta(days=1)), str(current_date))
            odoo.http.request.env.cr.execute(query)
            history_price = odoo.http.request.env.cr.dictfetchall()
            for idx, rec in enumerate(history_price):
                labels.append(str((rec.get('create_date') + datetime.timedelta(hours=7)).strftime("%Y-%m-%d %H:%M")))
                suggesting_price.append(rec.get('price'))
                my_competition.append(rec.get('my_competition'))
                super_competition.append(rec.get('s_competitor'))
                minimum_price.append(rec.get('min_price'))
                maximum_price.append(rec.get('max_price'))
                if idx != 0:
                    if rec.get('price') == history_price[idx-1].get('price'):
                        reason.append('')
                    else:
                        description = str()
                        if rec.get('rule') != history_price[idx-1].get('rule'):
                            description += "The rule has been changed from {} to {}. ".format(history_price[idx-1].get('rule'), rec.get('rule'))
                        if rec.get('search_type') != history_price[idx-1].get('search_type'):
                            description += "Search strategy has been changed from {} to {}. ".format(history_price[idx-1].get('search_type'), rec.get('search_type'))
                        else:
                            if rec.get('search_type' == 'Keyword') and rec.get('ebay_keyword') != history_price[idx-1].get('ebay_keyword'):
                                description += "Keyword has been changed from {} to {}. ".format(
                                    history_price[idx - 1].get('ebay_keyword'), rec.get('ebay_keyword'))
                        if rec.get('min_price') != history_price[idx-1].get('min_price'):
                            description += "Minumum price has been changed from {} to {}. ".format(history_price[idx - 1].get('min_price'), rec.get('min_price'))

                        if rec.get('max_price') != history_price[idx-1].get('max_price'):
                            description += "Minumum price has been changed from {} to {}. ".format(history_price[idx - 1].get('min_price'), rec.get('min_price'))

                        if rec.get('my_competition') != history_price[idx - 1].get('my_competition'):
                            description += "My competition price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('my_competition'), rec.get('my_competition'))

                        reason.append(description)
                else:
                    reason.append('')



        elif group_by == 'week':
            thisweek = (datetime.datetime.now() + datetime.timedelta(hours=7)).isocalendar()[1]
            Convert_Day = {
                0: 'Monday',
                1: 'Tuesday',
                2: 'Wednesday',
                3: 'Thursday',
                4: 'Friday',
                5: 'Saturday',
                6: 'Sunday'
            }
            reason_description = []
            for i in range(0,7):
                current_date = (datetime.datetime.now() + datetime.timedelta(hours=7) - datetime.timedelta(days=i)).date()
                if current_date.isocalendar()[1] != thisweek:
                    break
                query = """
                                select * from public.ebay_listing_item
                                    where "listId" = {} and create_date >=  '{} 17:00:00' and create_date < '{} 17:00:00'
                                    order by create_date ASC
                                            """.format(id, str(current_date - datetime.timedelta(days=1)),
                                                       str(current_date))
                odoo.http.request.env.cr.execute(query)
                history_price = odoo.http.request.env.cr.dictfetchall()
                if len(history_price) == 0:
                    continue
                sum_suggesting_price = 0
                sum_my_competition = 0
                sum_super_competition = 0
                sum_minimum_price = 0
                sum_maximum_price = 0
                description_in_this_day = str()
                for idx, rec in enumerate(history_price):
                    sum_suggesting_price += rec.get('price')
                    sum_my_competition += rec.get('my_competition')
                    sum_super_competition += rec.get('s_competitor')
                    sum_maximum_price += rec.get('max_price')
                    sum_minimum_price += rec.get('min_price')
                    description = str()
                    if idx != 0 and rec.get('price') != history_price[idx - 1].get('price'):
                        if rec.get('rule') != history_price[idx - 1].get('rule'):
                            description += "The rule has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('rule'), rec.get('rule'))
                        if rec.get('search_type') != history_price[idx - 1].get('search_type'):
                            description += "Search strategy has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('search_type'), rec.get('search_type'))
                        else:
                            if rec.get('search_type' == 'Keyword') and rec.get('ebay_keyword') != history_price[
                                idx - 1].get('ebay_keyword'):
                                description += "Keyword has been changed from {} to {}. ".format(
                                    history_price[idx - 1].get('ebay_keyword'), rec.get('ebay_keyword'))
                        if rec.get('min_price') != history_price[idx - 1].get('min_price'):
                            description += "Minumum price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('min_price'), rec.get('min_price'))

                        if rec.get('max_price') != history_price[idx - 1].get('max_price'):
                            description += "Minumum price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('min_price'), rec.get('min_price'))

                        if rec.get('my_competition') != history_price[idx - 1].get('my_competition'):
                            description += "My competition price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('my_competition'), rec.get('my_competition'))
                        if description:
                            description_in_this_day += "At {}, ".format((
                                                                                rec.get('create_date') + datetime.timedelta(hours=7)
                                                                        ).strftime("%Y-%m-%d %H:%M"))
                            description_in_this_day += description
                            description_in_this_day += '\n'



                if len(history_price) == 0:
                    continue
                else:
                    labels.insert(0,Convert_Day.get(current_date.weekday()))
                    suggesting_price.insert(0, round(float(sum_suggesting_price/len(history_price)), 2))
                    my_competition.insert(0, round(float(sum_my_competition / len(history_price)), 2))
                    super_competition.insert(0, round(float(sum_super_competition/len(history_price)), 2))
                    minimum_price.insert(0, round(float(sum_minimum_price/len(history_price)), 2))
                    maximum_price.insert(0, round(float(sum_maximum_price/len(history_price)), 2))
                    reason_description.insert(0, description_in_this_day)
            print(len(suggesting_price))
            print(len(reason_description))
            for idx, suggested_price in enumerate(suggesting_price):
                if idx == 0:
                    reason.append("")
                    continue
                if suggested_price != suggesting_price[idx - 1]:
                    if not reason_description[idx]:
                        reason.append(reason_description[idx])
                    else:
                        reason.append(reason_description[idx-1])
                else:
                    reason.append("")


        else:
            thismonth = (datetime.datetime.now() + datetime.timedelta(hours=7)).month
            reason_description = []
            for i in range(0, 31):

                current_date = (
                        datetime.datetime.now() + datetime.timedelta(hours=7) - datetime.timedelta(days=i)).date()
                if current_date.month != thismonth:
                    break
                query = """
                                                select * from public.ebay_listing_item
                                                    where "listId" = {} and create_date >=  '{} 17:00:00' and create_date < '{} 17:00:00'
                                                    order by create_date ASC
                                                            """.format(id,
                                                                       str(current_date - datetime.timedelta(days=1)),
                                                                       str(current_date))
                odoo.http.request.env.cr.execute(query)
                history_price = odoo.http.request.env.cr.dictfetchall()
                if len(history_price) == 0:
                    continue
                sum_suggesting_price = 0
                sum_my_competition = 0
                sum_super_competition = 0
                sum_minimum_price = 0
                sum_maximum_price = 0
                description_in_this_day = str()
                for idx, rec in enumerate(history_price):
                    sum_suggesting_price += rec.get('price')
                    sum_my_competition += rec.get('my_competition')
                    sum_super_competition += rec.get('s_competitor')
                    sum_maximum_price += rec.get('max_price')
                    sum_minimum_price += rec.get('min_price')
                    description = str()
                    if idx != 0 and rec.get('price') != history_price[idx - 1].get('price'):
                        if rec.get('rule') != history_price[idx - 1].get('rule'):
                            description += "The rule has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('rule'), rec.get('rule'))
                        if rec.get('search_type') != history_price[idx - 1].get('search_type'):
                            description += "Search strategy has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('search_type'), rec.get('search_type'))
                        else:
                            if rec.get('search_type' == 'Keyword') and rec.get('ebay_keyword') != history_price[
                                idx - 1].get('ebay_keyword'):
                                description += "Keyword has been changed from {} to {}. ".format(
                                    history_price[idx - 1].get('ebay_keyword'), rec.get('ebay_keyword'))
                        if rec.get('min_price') != history_price[idx - 1].get('min_price'):
                            description += "Minumum price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('min_price'), rec.get('min_price'))

                        if rec.get('max_price') != history_price[idx - 1].get('max_price'):
                            description += "Minumum price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('min_price'), rec.get('min_price'))

                        if rec.get('my_competition') != history_price[idx - 1].get('my_competition'):
                            description += "My competition price has been changed from {} to {}. ".format(
                                history_price[idx - 1].get('my_competition'), rec.get('my_competition'))
                        if description:
                            description_in_this_day += "At {}, ".format((
                                                                                rec.get(
                                                                                    'create_date') + datetime.timedelta(
                                                                            hours=7)
                                                                        ).strftime("%Y-%m-%d %H:%M"))
                            description_in_this_day += description
                            description_in_this_day += '\n'

                if len(history_price) == 0:
                    continue
                else:
                    labels.insert(0,str(current_date.strftime("%Y-%m-%d")))
                    suggesting_price.insert(0, round(float(sum_suggesting_price / len(history_price)), 2))
                    my_competition.insert(0, round(float(sum_my_competition / len(history_price)), 2))
                    super_competition.insert(0, round(float(sum_super_competition / len(history_price)), 2))
                    minimum_price.insert(0, round(float(sum_minimum_price / len(history_price)), 2))
                    maximum_price.insert(0, round(float(sum_maximum_price / len(history_price)), 2))
                    reason_description.insert(0, description_in_this_day)

            print(len(suggesting_price))
            print(len(reason_description))
            for idx, suggested_price in enumerate(suggesting_price):
                if idx == 0:
                    reason.append("")
                    continue
                if suggested_price != suggesting_price[idx - 1]:
                    if reason_description[idx]:
                        reason.append(reason_description[idx])
                    elif reason_description[idx-1]:
                        reason.append(reason_description[idx - 1])
                    else:

                        query = """
                                                                        select * from public.ebay_listing_item
                                                                            where "listId" = {} and create_date >=  '{} 17:00:00' and create_date < '{} 17:00:00'
                                                                            order by create_date ASC
                                                                                    """.format(id,
                                                                                               labels[idx].replace(labels[idx].split('-')[2],str(int(labels[idx].split('-')[2])-2)),
                                                                                               labels[idx])
                        odoo.http.request.env.cr.execute(query)
                        history_price = odoo.http.request.env.cr.dictfetchall()
                        description_in_this_day = str()
                        for _idx, rec in enumerate(history_price):
                            description = str()
                            if history_price[_idx].get('rule') != history_price[_idx - 1].get('rule'):
                                description += "The rule has been changed from {} to {}. ".format(
                                    history_price[_idx - 1].get('rule'), history_price[_idx].get('rule'))
                            if history_price[_idx].get('search_type') != history_price[_idx - 1].get('search_type'):
                                description += "Search strategy has been changed from {} to {}. ".format(
                                    history_price[_idx - 1].get('search_type'), history_price[_idx].get('search_type'))
                            else:
                                if history_price[_idx].get('search_type' == 'Keyword') and history_price[_idx].get('ebay_keyword') != history_price[
                                    _idx - 1].get('ebay_keyword'):
                                    description += "Keyword has been changed from {} to {}. ".format(
                                        history_price[_idx - 1].get('ebay_keyword'), history_price[_idx].get('ebay_keyword'))
                            if history_price[_idx].get('min_price') != history_price[_idx - 1].get('min_price'):
                                description += "Minumum price has been changed from {} to {}. ".format(
                                    history_price[_idx - 1].get('min_price'), history_price[_idx].get('min_price'))

                            if history_price[_idx].get('max_price') != history_price[_idx - 1].get('max_price'):
                                description += "Minumum price has been changed from {} to {}. ".format(
                                    history_price[_idx - 1].get('min_price'), history_price[_idx].get('min_price'))

                            if history_price[_idx].get('my_competition') != history_price[_idx - 1].get('my_competition'):
                                description += "My competition price has been changed from {} to {}. ".format(
                                    history_price[_idx - 1].get('my_competition'), history_price[_idx].get('my_competition'))
                            if description:
                                description_in_this_day += "At {}, ".format((
                                                                                    history_price[_idx].get(
                                                                                        'create_date') + datetime.timedelta(
                                                                                hours=7)
                                                                            ).strftime("%Y-%m-%d %H:%M"))
                                description_in_this_day += description
                                description_in_this_day += '\n'
                        reason.append(description_in_this_day)
                else:
                    reason.append("")

        response = {
            "label": labels,
            "suggesting": suggesting_price,
            'my_competition': my_competition,
            "super_competition": super_competition,
            "minimum_price": minimum_price,
            "maximum_price": maximum_price,
            'reason': reason

        }

        # response = {
        #     "status": "error",
        #     "content": "not found"
        # }

        return json.dumps(response)