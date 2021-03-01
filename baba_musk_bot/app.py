import json
import telegram
import os
import logging
import json
import yfinance as yf
from telegram import BotCommand
from functools import wraps

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

def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


def parse_ticker_symbol(symbol):
    if symbol[0] == '$':
        symbol = symbol[1:]
    return symbol


def ticker_check(symbol, tick):
    ticker = parse_ticker_symbol(symbol)
    try:
        logging.info(tick.info)
    except:
        logging.warning('Ticker {} does not exist'.format(ticker))
        return {'ticker': ticker, 'valid': False}
    return {'ticker': ticker, 'valid': True}

def ytd(symbol):
    ticker = parse_ticker_symbol(symbol)
    tick = yf.Ticker(ticker)
    if ticker_check(ticker, tick)['valid']:
        first_trading_day_timestamp = tick.history(period="ytd").first_valid_index()
        last_trading_day_timestamp = tick.history(period="ytd").last_valid_index()
        first_day_open = tick.history(period="ytd")['Open'].values[0]
        last_day_close = tick.history(period="ytd")['Close'].values[len(tick.history(period="ytd").index) - 1]
        percent_change = ((last_day_close / first_day_open) - 1) * 100
        move = 'up' if percent_change > 0 else 'down'
        return '\n${0} is {2} {1} % this year.\n'.format(ticker, format(percent_change, '.2f'), move)
    else:
        logging.warning('Ticker {} does not exist'.format(ticker))
        return '\n{} not found.\n'.format(ticker)


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
                                BotCommand(command='describe', description='''Get Help''')
                                ])

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received')
        update = telegram.Update.de_json(json.loads(event.get('body')), bot)
        try:
            chat_id = update.message.chat.id
            sender = update.message.from_user.first_name
            try:
                text = update.message.text
            except:
                text = '/describe'
        except AttributeError:
            chat_id = update.edited_message.chat_id
            sender = update.edited_message.from_user.first_name
            try:
                text = update.edited_message.text
            except:
                text = '/describe'

        if text.strip() == '/hello' or text.strip() == '/hello@BabaMuskBot':
            response_text = """Hello {0}, \n I am an BabaMusk bot, built with Python and the AWS Serverless Application Model (SAM) Framework.""".format(sender)

        elif text.strip() == '/ytd' or text.strip() == '/ytd@BabaMuskBot':
            response_text = """Please provide a ticker symbol e.g. /ytd AMZN""".format(sender)

        elif text.startswith('/ytd') and len(text.split(' ')) > 1:
            response_text = ''
            tick_list = list(filter(lambda x: x != '/ytd', text.split(' ')))
            for tick in tick_list:
                response_text = response_text + ytd(tick)

        elif text.strip() == '/describe' or text.strip() == '/describe@BabaMuskBot':
            response_text = '''You can run the following commands \n /hello : Start talking to this bot \n /ytd : Calculates stock's performance year-to-date \n /describe : Displays this message '''

        else:
            response_text = text

        if response_text == text:
            pass
        else:
            bot.sendMessage(chat_id=chat_id, text=response_text)

        logger.info('Message sent')

        return OK_RESPONSE

    return ERROR_RESPONSE
