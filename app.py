import config as cfg
from wallet import Wallet
from data import NetworkSettings
from exceptions import *
from constants import *

from tinkoff.invest import Client as t_Client
from binance.client import Client
from binance.enums import *
from binance.exceptions import *
from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://rskulrdesqfsgr:7c78c961bac280e642345070c82a6efcbfd2116a1827ba783bcc3a988fa81dd5@ec2-52-208-221-89.eu-west-1.compute.amazonaws.com:5432/dp7a48a0n88re'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app_context = app.app_context()
settings = NetworkSettings(api_secret=None, api_key=None)
wallet = Wallet()
db = SQLAlchemy(app)


class Info(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    api_key = db.Column(db.String(255), nullable=False)
    api_secret = db.Column(db.String(255), nullable=False)
    tg_token = db.Column(db.String(255), nullable=False)
    chat_id = db.Column(db.String(255), nullable=False)
    fee = db.Column(db.Float(), nullable=False)


class Stats(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    deals = db.Column(db.Integer(), nullable=False)
    profit = db.Column(db.Float(), nullable=False)
    fees = db.Column(db.Float(), nullable=False)
    clean_profit = db.Column(db.Float(), nullable=False)


class TinkoffInfo(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    api_key = db.Column(db.String(255), nullable=False)
    account_id = db.Column(db.String(255), nullable=False)
    fee = db.Column(db.Float(), nullable=False)


class TinkoffStat(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    deals = db.Column(db.Integer(), nullable=False)
    profit = db.Column(db.Float(), nullable=False)
    fees = db.Column(db.Float(), nullable=False)
    clean_profit = db.Column(db.Float(), nullable=False)


def order(side, qty, ticker, order_type=ORDER_TYPE_MARKET):
    """
    Выставляет ордер на покупку или продажу
    :param side: BUY/SELL
    :param qty: Количество покупаемой/продаваемой крипты. Определяется источником веб-хука
    :param ticker: Торговая пара. Определяется источником веб-хука
    :param order_type: Тип ордера: Market, Limit. По умолчанию: Market
    :return:
    """
    try:
        last_info = get_info(BINANCE)
        print(f'Выставляем ордер {order_type} - {side} {qty} {ticker}')
        client = Client(api_key=last_info.api_key, api_secret=last_info.api_secret)
        order = client.create_order(
            symbol=ticker,
            side=side,
            type=order_type,
            quantity=qty,
        )
        return order
    except Exception as e:
        print(f'Произошла ошибка - {e}')
        last_info = get_info(BINANCE)
        wallet.notify_error(e, last_info.tg_token, last_info.chat_id)
        return False


def get_stat(exchange):
    """
    Получает статистику в зависимости от выбранной биржи
    :param exchange:
    :return:
    """
    if exchange.lower() == BINANCE:
        stats = Stats.query.all()
        stats = stats[-1]
        return stats
    if exchange.lower() == TINKOFF:
        t_stats = TinkoffStat.query.all()
        t_stats = t_stats[-1]
        return t_stats
    else:
        tg = get_info(BINANCE)
        wallet.notify_error(WrongExchange(), tg.tg_token, tg.chat_id)


def get_info(exchange):
    """
    Получает информацию о аккаунте бинанса или тинькофф или отсылает уведомление о неправильно введенной бирже.
    :param exchange:
    :return:
    """
    if exchange.lower() == BINANCE:
        info = Info.query.all()
        last_info = info[-1]
        return last_info
    if exchange.lower() == TINKOFF:
        info = TinkoffInfo.query.all()
        last_info = info[-1]
        return last_info
    else:
        tg = get_info(BINANCE)
        wallet.notify_error(WrongExchange(), tg.tg_token, tg.chat_id)


def mutate_stat(data, stats, info, buy):
    size = float(data['strategy']['order_contracts']) * float(data['bar']['close'])
    stats.fees += size * float(info.fee)
    if buy:
        stats.profit -= size
    else:
        stats.profit += size
        stats.deals += 1
    stats.clean_profit = stats.profit - stats.fees


def deal(data, tg_token, chat_id, exchange):
    """
    Обновляет информацию в кошельке, после совершения покупки или продажи, работает для Tinkoff
    :param exchange:
    :param chat_id:
    :param tg_token:
    :param data:
    :return:
    """
    tink_info = get_info(exchange)
    stats = get_stat(exchange)
    if data['strategy']['order_action'].lower() == 'buy':
        mutate_stat(data, stats, tink_info, buy=True)
        try:
            db.session.commit()
        except:
            raise Exception
        wallet.buy(
            float(data['bar']['close']),
            float(data['strategy']['order_contracts']),
            data['ticker'],
            _tg_token=tg_token,
            _chat_id=chat_id,
        )
    else:
        mutate_stat(data, stats, tink_info, buy=False)
        try:
            db.session.commit()
        except:
            raise Exception
        wallet.sell(
            float(data['bar']['close']),
            data['ticker'],
            amount=float(data['strategy']['order_contracts']),
            _tg_token=tg_token,
            _chat_id=chat_id,
        )
        summary = f'\n#Сводка{exchange.upper()}\n' \
                  f'Продан #{data["ticker"][:-4]}:\n' \
                  f'Общее кол-во сделок: {stats.deals}\n' \
                  f'Профит: ${round(stats.profit, 2)}\n' \
                  f'Профит за вычетом комиссий: ${round(stats.clean_profit, 2)}\n' \
                  f'Уплачено комиссий: ${round(stats.fees, 2)}\n'
        wallet._notify(summary, tg_token, chat_id)


def check_if_valid(data):
    """
    Проверяет правильный ли пароль был отправлен вместе с вебхуком
    :param data:
    :return:
    """
    last_info = get_info(BINANCE)
    try:
        if data['pass'] != cfg.PASS:
            wallet.notify_error(WrongPassword(), last_info.tg_token, last_info.chat_id)
            return False
        else:
            return True
    except:
        wallet.notify_error('Пароль не найден в веб-хуке!', last_info.tg_token, last_info.chat_id)
        return False


def check_token():
    try:
        info = Info.query.all()
        last_info = info[-1]
    except:
        return 'Отсутствуют'

    if last_info.tg_token and last_info.chat_id:
        return 'Присутствуют'
    else:
        wallet.notify_error('Проверка уведомлений', last_info.tg_token, last_info.chat_id)
        return 'Отсутствуют'


def check_tinkoff_client():
    """
    Пытаестся создать тестовый ордер для проверки наличия API ключей Tinkoff,
    путем получения баланса
    :return:
    """
    try:
        t_info = TinkoffInfo.query.all()
        last_info = t_info[-1]
    except:
        client_status = 'Отсутствуют'
        return client_status
    try:
        with t_Client(last_info.api_key) as actual_client:
            from tink_sub import get_free_money
            ping = get_free_money(actual_client, int(last_info.account_id))
            print("Tinkoff Client check: ", ping)
        client_status = 'Предоставлено'
        return client_status
    except:
        # For telegram token and chat id
        last = get_info(BINANCE)
        wallet.notify_error(f'<Tinkoff> У вас отсутствуют или неверно введены API-ключи!', last.tg_token, last.chat_id)
        client_status = 'Отсутствуют'
        return client_status


def check_client():
    """
    Пытаестся создать тестовый ордер для проверки наличия API ключей,
    если просто пинговать или получать инфу по тикерам, то ошибку не выдает
    :return:
    """
    try:
        last_info = get_info(BINANCE)
    except:
        client_status = 'Отсутствуют'
        return client_status
    try:
        actual_client = Client(api_key=str(last_info.api_key), api_secret=str(last_info.api_secret))
        ping = actual_client.create_test_order(symbol='BTCUSDT',
                                               side=SIDE_BUY,
                                               type=ORDER_TYPE_MARKET,
                                               quantity=0.1,
                                               )
        print("Client check: ", ping)
        client_status = 'Предоставлено'
        return client_status
    except:
        wallet.notify_error(f'У вас отсутствуют или неверно введены API-ключи!', last_info.tg_token, last_info.chat_id)
        client_status = 'Отсутствуют'
        return client_status


def set_stat_t():
    """
    Statistics for tinkoff trading
    :return:
    """
    try:
        statistic = TinkoffStat.query.all()
        statistic = statistic[-1]
        res = {
            'deals': statistic.deals,
            'profit': statistic.profit,
            'fee': statistic.fees,
            'clean_profit': statistic.clean_profit,
        }
        return res
    except:
        first_stat = TinkoffStat(deals=0, profit=0.0, fees=0.0, clean_profit=0.0)
        with app_context:
            db.session.add(first_stat)
            db.session.commit()
            res = {
                'deals': 0,
                'profit': 0.0,
                'fee': 0.0,
                'clean_profit': 0.0,
            }
        return res


def set_stat():
    """
    Statistics for crypto-trading
    :return:
    """
    try:
        statistic = Stats.query.all()
        statistic = statistic[-1]
        res = {
            'deals': statistic.deals,
            'profit': statistic.profit,
            'fee': statistic.fees,
            'clean_profit': statistic.clean_profit,
        }
        return res
    except:
        first_stat = Stats(deals=0, profit=0.0, fees=0.0, clean_profit=0.0)
        with app_context:
            db.session.add(first_stat)
            db.session.commit()
            res = {
                'deals': 0,
                'profit': 0.0,
                'fee': 0.0,
                'clean_profit': 0.0,
            }
        return res


@app.route('/set_params', methods=['POST', 'GET'])
def params():
    if request.method == 'POST' and request.form['password'] == cfg.PASS:
        api_key = request.form['api_key']
        api_secret = request.form['api_secret']
        tg_token = request.form['tg_token']
        chat_id = request.form['chat_id']
        fee = request.form['fee']

        info = Info(
            api_key=api_key,
            api_secret=api_secret,
            tg_token=tg_token,
            chat_id=chat_id,
            fee=fee,
        )
        with app_context:
            db.session.add(info)
            db.session.commit()
        return redirect('/')
    else:
        return render_template('update_info.html')


@app.route('/set_params_tinkoff', methods=['POST', 'GET'])
def params_t():
    if request.method == 'POST' and request.form['password'] == cfg.PASS:
        api_key = request.form['api_key']
        fee = request.form['fee']
        try:
            with t_Client(api_key) as client:
                resp = client.users.get_accounts()
                print(resp.accounts)
                acc_id = resp.accounts[0].id
        except:
            return render_template('tinkoff_info.html',context={'error':'Неправильно введены данные!'})
        Tinfo = TinkoffInfo(
            api_key=api_key,
            fee=fee,
            account_id=acc_id,
        )
        with app_context:
            db.session.add(Tinfo)
            db.session.commit()
        return redirect('/')
    else:
        return render_template('tinkoff_info.html', context={'error':''})


@app.route('/')
def hello_world():
    """
    Возвращает главную страницу, проверяет целостность бота, работоспособность всех функций
    :return:
    """
    # Функционал бота
    client_status = check_client()
    notifications_status = check_token()
    t_client_status = check_tinkoff_client()

    # Статистика
    stats = set_stat()
    stats_t = set_stat_t()
    context = {
        'client': client_status,
        'notifications': notifications_status,
        't_client': t_client_status,
        'stat': {
            'deals': stats['deals'],
            'total_fee': round(stats['fee'], 2),
            'profit': round(stats['profit'], 2),
            'clean_profit': round(stats['clean_profit'], 2),
        },
        'stat_t': {
            'deals': stats_t['deals'],
            'total_fee': round(stats_t['fee'], 2),
            'profit': round(stats_t['profit'], 2),
            'clean_profit': round(stats_t['clean_profit'], 2),
        }
    }
    return render_template('base.html', context=context)


@app.route('/webhook', methods=['POST'])
def webhook():
    # Info of binance to get telegram token and chat id
    last_info = get_info(BINANCE)
    data = json.loads(request.data)
    # Checking if request password is valid
    if not check_if_valid(data):
        return {
            'code': 'error'
        }

    # Placing an order
    order_response = order(data['strategy']['order_action'].upper(),
                           float(data['strategy']['order_contracts']),
                           data['ticker'])
    if order_response:
        deal(data, last_info.tg_token, last_info.chat_id, BINANCE)
        return {
            'response': order_response
        }
    else:
        wallet.notify_error(OrderWasNotPlaced(), last_info.tg_token, last_info.chat_id)
        return {
            'response': False
        }


@app.route("/webhook_tinkoff", methods=["POST"])
def webhook_tinkoff():
    # importing module with tinkoff functions
    import tink_sub as t
    # Info of Tinkoff to get tinkoff credentials
    last = get_info(TINKOFF)
    # Info of binance to get telegram token and chat id
    last_info = get_info(BINANCE)
    try:
        if request.method == "POST":
            data = request.get_json()
            if not check_if_valid(data):
                return {
                    'code': 'error'
                }
            else:
                print(t.get_timestamp(), "Alert Received & Sent!")
                order_response, msg = t.make_order_tick(data, str(last.account_id), last.api_key)

            if order_response:
                deal(data, last_info.tg_token, last_info.chat_id, TINKOFF)
                return {
                    'response': order_response
                }
            else:
                wallet.notify_error(msg, last_info.tg_token, last_info.chat_id)
                return {
                    'response': False
                }

    except Exception as e:
        print("[X]", t.get_timestamp(), "Error:\n>", e)
        return "Error", 400
