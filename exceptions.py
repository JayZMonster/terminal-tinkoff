
class WrongPassword(Exception):

    def __str__(self):
        return 'Введен неверный пароль!'


class OrderWasNotPlaced(Exception):

    def __str__(self):
        return 'Ордер не был выставлен!'


class WrongExchange(Exception):

    def __str__(self):
        return 'В сообщении от TradingView указан неверный обменник!'
