from datetime import datetime
import requests


class Wallet:

    def __init__(self):
        """
        :param fee: - platform's fee size
        """
        self.fee_size = None
        self.client = None
        self.bought = 0
        self.sold = 0
        self.trades = 0
        self.total_fee = 0
        self.shares = 0
        self.profit = round(self.sold - self.bought, 2)
        self.start_date = datetime.now()
        self.last_timestamp = None
        self.token = None
        self.chat_id = None

    def get_crypto_bank(self):
        """
        Currently bought quantity of currency.
        :return:
        """
        return self.shares

    def summary(self, ticker: str):
        """
        Shows summary report, with all the stats
        :return:
        """
        summary = f'\n#Сводка\n' \
                  f'Продан #{ticker[:-4]}:\n'\
                  f'Общее кол-во сделок: {self.trades}\n'\
                  f'Профит: ${self.profit}\n'\
                  f'Профит за вычетом комиссий: ${round(self.profit - self.total_fee, 2)}\n' \
                  f'Уплачено комиссий: ${round(self.total_fee, 2)}\n'
        return summary

    def _notify(self, msg, _token, _chat_id):
        url = f"https://api.telegram.org/bot{_token}/sendMessage"
        msg_data = {
            'chat_id': _chat_id,
            'text': msg,
            'parse_mode': 'HTML'
        }
        requests.post(url, data=msg_data)

    def notify_error(self, e, _token, _chat_id):
        msg = f'{datetime.now()}\n#ERROR\nВозникла ошибка: {e}\n' \
              f'Если это сообщение повторяется неоднократно, значит нужно чинить!\n' \
              f'Напишите в тг: @JayZAnsh'
        self._notify(msg, _token, _chat_id)

    def notify_deal(self, deal_type, timestamp, amount, ticker, price, _token, _chat_id, report=False) -> None:
        msg = f'{timestamp}\n #{deal_type} {amount} #{ticker} по цене ${price}\n' \
              f'На сумму ${round(float(amount)*float(price), 2)}'
        self._notify(msg, _token, _chat_id)

    def buy(self, price: float, amount: float, ticker: str, _tg_token, _chat_id):
        self._buy(price, amount, ticker, _tg_token, _chat_id)

    def sell(self, price: float, ticker: str, amount: float, _tg_token, _chat_id):
        self._sell(price, ticker, amount, _tg_token, _chat_id)

    def _buy(self, price: float, amount: float, ticker: str, _tg_token, _chat_id) -> None:
        """
        Implements buying process, calculates fee
        :param price:
        :return:
        """
        self.notify_deal(deal_type='Куплено',
                         timestamp=datetime.now(),
                         amount=amount,
                         ticker=ticker,
                         price=price,
                         _token=_tg_token,
                         _chat_id=_chat_id,
                         )

    def _sell(self, price: float, ticker: str, amount: float, _tg_token, _chat_id) -> None:
        """
        Implements selling process
        :param price:
        :return:
        """
        self.notify_deal(deal_type='Продано',
                         timestamp=datetime.now(),
                         amount=amount,
                         ticker=ticker,
                         price=price,
                         report=True,
                         _token=_tg_token,
                         _chat_id=_chat_id,
                         )
        self.shares = 0


# if __name__ == '__main__':
#     wal = Wallet(start_bank=1000.0,
#                  fee=0.0075,
#                  percents=0.2,
#                  ticker="BTCBUSD",
#                  )
#     from exceptions import TechnicalIndicatorsError
#     wal.chat_id = 517321921
#     wal.token = '5267388557:AAEzz1Bi_vjwUxJXO8Icp5cDLszTGPkx52s'
#     wal.buy(35000, 0.5)
