import json
import requests
import emoji
import telegram
import os
import logging
import yfinance as yf
from telegram import BotCommand
from datetime import date, timedelta

# Logging is cool!
logger = logging.getLogger()

if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

logging.basicConfig(level=logging.INFO)

OK_RESPONSE = {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps('ok')
}
ERROR_RESPONSE = {
    'statusCode': 400,
    'body': json.dumps('Oops, something went wrong!')
}

POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')


def configure_telegram():
    """
    Configures the bot with a Telegram Token.
    Returns a bot instance.
    """

    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

    if not TELEGRAM_TOKEN:
        logger.error('The TELEGRAM_TOKEN must be set')
        raise NotImplementedError

    return telegram.Bot(TELEGRAM_TOKEN)


def parse_ticker_symbol(symbol):
    if symbol[0] == '$':
        symbol = symbol[1:]
    return symbol


def ticker_check(symbol):
    ticker = parse_ticker_symbol(symbol)
    ticker_url = f'https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={POLYGON_API_KEY}'
    response = requests.get(ticker_url)
    response_dict = dict(response.json())

    if response_dict['status'] == 'NOT_FOUND':
        return {'ticker': ticker, 'valid': False}

    return {'ticker': ticker, 'valid': True}

def implied_market_status(status_date):
    get_implied_market_status_url = f'https://api.polygon.io/v1/open-close/AAPL/{status_date}?adjusted=true&apiKey={POLYGON_API_KEY}'
    response = requests.get(get_implied_market_status_url)
    response_dict = dict(response.json())

    if response_dict['status'] == 'NOT_FOUND':
        return False

    return True


def first_trading_date():
    today = date.today()
    start_date = date(today.year, 1, 1)
    while True:
        if date.weekday(start_date) in range(0, 5) and implied_market_status(start_date.strftime('%Y-%m-%d')):
            start_date = start_date
            break
        elif date.weekday(start_date) in range(0, 5) and implied_market_status(start_date.strftime('%Y-%m-%d')) is False:
            start_date = start_date + timedelta(days=1)
        elif date.weekday(start_date) == 5:
            start_date = start_date + timedelta(days=2)
        else:
            start_date = start_date + timedelta(days=1)

    return start_date


def last_trading_date():
    start_date = date.today()
    while True:
        if date.weekday(start_date) in range(0, 5) and implied_market_status(
                start_date.strftime('%Y-%m-%d')):
            start_date = start_date
            break
        elif date.weekday(start_date) in range(0, 5) and implied_market_status(
                start_date.strftime('%Y-%m-%d')) is False:
            start_date = start_date - timedelta(days=1)
        elif date.weekday(start_date) == 5:
            start_date = start_date - timedelta(days=1)
        else:
            start_date = start_date - timedelta(days=2)

    return start_date


def ytd(symbol):
    ticker = parse_ticker_symbol(symbol)
    tick = yf.Ticker(ticker)

    logging.info(f'The first trading day was {first_trading_date()}')

    if ticker_check(ticker)['valid']:
        first_day_open = None
        last_day_close = None
        while True:
            if first_day_open is None:
                get_first_day_data = dict(requests.get(
                    f'https://api.polygon.io/v1/open-close/AAPL/{first_trading_date()}?adjusted=true&apiKey={POLYGON_API_KEY}').json())
                print(get_first_day_data)
                if get_first_day_data['status'] == 'OK':
                    first_day_open = get_first_day_data['open']
                    time.sleep(5)
                else:
                    time.sleep(61)

            if last_day_close is None:
                get_last_day_data = dict(requests.get(
                    f'https://api.polygon.io/v1/open-close/AAPL/{last_trading_date()}?adjusted=true&apiKey={POLYGON_API_KEY}').json())
                print(get_last_day_data)
                if get_last_day_data['status'] == 'OK':
                    last_day_close = get_last_day_data['close']
                    time.sleep(5)
                else:
                    time.sleep(61)

            if first_day_open is not None and last_day_close is not None:
                break

        percent_change = ((last_day_close / first_day_open) - 1) * 100

        move = ':arrow_up_small:' if percent_change > 0 else ':arrow_down_small:'
        return emoji.emojize(
            '\n<a href="https://robinhood.com/stocks/{0}">{0}</a> is {2} {1} % this year\n'.format(ticker.upper(), format(percent_change, '.2f'), move),
            use_aliases=True)
    else:
        logging.warning('Ticker {} does not exist'.format(ticker))
        return '\n{} not found.\n'.format(ticker)


def describe(symbol):
    ticker = parse_ticker_symbol(symbol)
    tick = yf.Ticker(ticker)
    if ticker_check(ticker)['valid']:
        try:
            ticker_url = f'https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={POLYGON_API_KEY}'
            response = requests.get(ticker_url)
            response_dict = dict(response.json())
            description = response_dict['results']['description']
        except:
            description = False
        if not description:
            return 'No description found'
        else:
            return '\n<b>{0}</b>\n{1}\n'.format(ticker.upper(), description)
    else:
        logging.warning('Ticker {} does not exist'.format(ticker))
        return '\n{} not found.\n'.format(ticker)


def coin():
    result = ''
    crypto_name = {'BTC': 'Bitcoin',
                   'ETH': 'Ethereum',
                   'ADA': 'Cardano',
                   'MATIC': 'Polygon',
                   'SOL': 'Solana'}
    for pairing in ['BTC-USD','ETH-USD','ADA-USD', 'MATIC-USD','SOL-USD','BTC-CAD','ETH-CAD','ADA-CAD', 'MATIC-CAD','SOL-CAD']:
        response = requests.get(f'''https://api.coinbase.com/v2/prices/{pairing}/spot''')
        data = response.json()
        country = ':Canada:' if data['data']['currency'] == 'CAD' else ':United_States:'
        result = result + '''1 {0} is ${2} in {3}\n'''.format(crypto_name[data['data']['base']], data['data']['currency'], format(float(data['data']['amount']),'.2f'), country)
    return emoji.emojize(result, use_aliases=True)


def set_webhook(event, context):
    """
    Sets the Telegram bot webhook.
    """

    logger.info('Event: {}'.format(event))
    bot = configure_telegram()
    url = 'https://{}/{}/'.format(
        event.get('headers').get('Host'),
        event.get('requestContext').get('stage'),
    )
    webhook = bot.set_webhook(url)

    if webhook:
        return OK_RESPONSE

    return ERROR_RESPONSE


def webhook(event, context):
    """
    Runs the Telegram webhook.
    """

    bot = configure_telegram()
    logger.info('Event: {}'.format(event))

    bot.setMyCommands(commands=[BotCommand(command='hello', description='''Start interaction'''),
                                BotCommand(command='ytd',
                                           description='''Calculates stock's performance year-to-date'''),
                                BotCommand(command='coin',
                                           description='''Get latest BTC price in USD/CAD'''),
                                BotCommand(command='desc',
                                           description='''Provides a summary about the business'''),
                                BotCommand(command='guide', description='''Get Help''')
                                ])

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received')
        update = telegram.Update.de_json(json.loads(event.get('body')), bot)

        try:
            chat_id = update.message.chat.id
            sender = update.message.from_user.first_name
            text = update.message.text
        except AttributeError:
            logging.error('No Message received frmm chat.')

        try:
            if text.strip() == '/hello' or text.strip() == '/hello@BabaMuskBot' or text.strip() == '/start' or text.strip() == '/start@BabaMuskBot':
                response_text = """Hello {0}, \nI am an BabaMusk bot, built with Python and the AWS Serverless Application Model (SAM) Framework.""".format(
                    sender)

            elif text.strip() == '/ytd' or text.strip() == '/ytd@BabaMuskBot':
                response_text = """Please provide a ticker symbol e.g. /ytd AMZN""".format(sender)

            elif text.strip() == '/coin' or text.strip() == '/coin@BabaMuskBot':
                response_text = coin()

            elif text.startswith('/ytd'):
                response_text = ''
                tick_list = list(filter(lambda x: x != '/ytd', text.split(' ')))
                if len(tick_list) <= 1:
                    for tick in tick_list:
                        response_text = response_text + ytd(tick)
                else:
                    response_text = '/ytd only supports 1 ticker.'''

            elif text.strip() == '/desc' or text.strip() == '/desc@BabaMuskBot':
                response_text = """Please provide a ticker symbol e.g. /describe AMZN""".format(sender)

            elif text.startswith('/desc') and len(text.split(' ')) > 1:
                response_text = ''
                tick_list = list(filter(lambda x: x != '/desc', text.split(' ')))
                for tick in tick_list:
                    response_text = response_text + describe(tick)

            elif text.strip() == '/guide' or text.strip() == '/guide@BabaMuskBot':
                response_text = '''You can run the following commands \n/hello : Start talking to this bot \n/ytd : Calculates stock's performance year\-to\-date \n/coin : Get latest BTC price in USD\n/describe : Provides a summary about the business \n/guide : Displays this message '''

            else:
                response_text = text

        except (AttributeError, UnboundLocalError):
            logging.warning('No Text received')
            return OK_RESPONSE

        if response_text == text:
            pass
        else:
            message = bot.sendMessage(chat_id=chat_id, text=response_text, parse_mode='HTML', disable_web_page_preview=True)
            logger.info(f'The message_id is {message.message_id}')
            logger.info(f'The chat_id is {message.chat.id}')

            '''ddb = boto3.client('dynamodb')

            response =  ddb.put_item(
                TableName='BabaMuskSentMessageStore',
                Item={'chat_message_id': {
                    'S': str(message.chat.id) + '_' + str(message.message_id)
                }}
            )

            logger.info(response)'''

        logger.info('Message sent')

        return OK_RESPONSE

    return ERROR_RESPONSE
