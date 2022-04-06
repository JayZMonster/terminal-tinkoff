import pprint
import time
from datetime import datetime

from tinkoff.invest import (
    Client,
    InstrumentIdType,
    RequestError,
    OrderDirection,
    Quotation,
    OrderType,
    OrderExecutionReportStatus,
)


def get_timestamp():
    timestamp = time.strftime("%Y-%m-%d %X")
    return timestamp


def to_num(elem):

    return elem.units + elem.nano / 1e9


def get_free_money(client_t, acc_id):

    ret_val = 0
    try:
        acc_sum = client_t.operations.get_withdraw_limits(account_id=str(acc_id))
        print(acc_sum)
        if acc_sum.money:
            ret_val = to_num(acc_sum.money[0]) - (to_num(acc_sum.blocked[0]) if len(acc_sum.blocked) > 0 else 0)
        else:
            return 'No money!'

    except RequestError as err:
        print('get_free_money error. Err_code - %s' % err.details)

    # print('get_free_money - %s' % ret_val)
    return ret_val


def get_figi_info(client_t, figi_name):

    ret_figi_lot = 0
    ret_price = 0
    try:
        price = client_t.market_data.get_last_prices(figi=[figi_name])
        if len(price.last_prices) > 0:
            ret_price = to_num(price.last_prices[0].price)

        figi_info = client_t.instruments.share_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                                                  class_code='', id=figi_name)
        ret_figi_lot = figi_info.instrument.lot

    except RequestError as err:
        print('get_figi_info error. Err_code - %s' % err.details)

    return ret_price, ret_figi_lot


def get_volume_buyed_figi(client_t, figi_name, acc_id):

    ret_val = 0
    try:
        poss = client_t.operations.get_portfolio(account_id=str(acc_id))
        for elem in poss.positions:
            if elem.figi == figi_name:
                ret_val += to_num(elem.quantity)

    except RequestError as err:
        print('get_volume_buyed_figi error. Err_code - %s' % err.details)

    return ret_val


def make_order_tick(data_s, acc_id, token):

    ticker = data_s['ticker']
    operation = data_s['strategy']['order_action']
    qty = data_s['strategy']['order_contracts']
    figi_name = None
    with Client(token) as tinkoff_client:
        data = tinkoff_client.instruments.shares()
        for share in data.instruments:
            if share.ticker == ticker:
                figi_name = share.figi
        if not figi_name:
            return 'No such stock!'
    with Client(token) as tinkoff_client:

        curr_price, figi_lot = get_figi_info(tinkoff_client, figi_name)

        if figi_lot != 0:
            if operation.lower() == 'buy':
                total_summ = get_free_money(tinkoff_client, acc_id)
                # определение количества - покупка на всю сумму
                quantity_to_buy = int(qty)
                # чисто для тестов - покупка 1 акции
                # quantity_to_buy = 1
                if quantity_to_buy > 0:
                    try:
                        a = tinkoff_client.orders.post_order(figi=figi_name, quantity=quantity_to_buy,
                                                             direction=OrderDirection.ORDER_DIRECTION_BUY,
                                                             account_id=str(acc_id),
                                                             order_type=OrderType.ORDER_TYPE_MARKET,
                                                             order_id='{}-{}'.format(datetime.now().strftime('%Y%m%d%H%M%S'),
                                                                                     figi_name))
                        if a.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL:
                            msg = '{} FIGI - {}, BUY. Order amount - {}, CURR_PRICE - {}'.format(datetime.now(), figi_name, to_num(a.total_order_amount), curr_price)
                            print(msg)
                        return 1, msg
                    except RequestError as err:
                        error = 'MAKE_ORDER BUY ERROR - {}, QUANTITY - {}, PRICE - {} TOTAL_SUM - {}'.format(err.details, quantity_to_buy, curr_price, total_summ)
                        print(error)
                        return 0, error
            if operation.lower() == 'sell':
                # продаем все что есть
                quantity = get_volume_buyed_figi(tinkoff_client, figi_name, acc_id) // figi_lot
                if quantity > 0:
                    try:
                        a = tinkoff_client.orders.post_order(figi=figi_name, quantity=int(quantity),
                                                             direction=OrderDirection.ORDER_DIRECTION_SELL,
                                                             account_id=str(acc_id),
                                                             order_type=OrderType.ORDER_TYPE_MARKET,
                                                             order_id='{}-{}'.format(datetime.now().strftime('%Y%m%d%H%M%S'),
                                                                                     figi_name))
                        if a.execution_report_status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL :
                            msg = '{} FIGI - {}, SELL. Order amount - {}, CURR_PRICE - {}'.format(datetime.now(), figi_name, to_num(a.total_order_amount), curr_price)
                            print(msg)
                        return 1, msg
                    except RequestError as err:
                        error = 'MAKE_ORDER SELL ERROR - {}'.format(err.details)
                        print(err)
                        return 0, error


