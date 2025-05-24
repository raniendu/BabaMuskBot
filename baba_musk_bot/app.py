"""
BabaMuskBot: A Serverless Telegram Bot for Stock and Cryptocurrency Information.

This AWS Lambda application, deployed using AWS SAM, provides a Telegram bot
interface for users to query real-time stock market data (Year-To-Date performance,
company descriptions) via the Polygon.io API, and cryptocurrency prices via the
Coinbase API.

Key functionalities include:
- Parsing user commands received through Telegram.
- Validating stock ticker symbols.
- Fetching and calculating Year-To-Date (YTD) stock performance.
- Retrieving company descriptions.
- Fetching current prices for major cryptocurrencies.
- Handling API errors gracefully with retries and user feedback.
- Securely managing API keys using AWS Systems Manager Parameter Store.

The main handler for Telegram webhook events is the `webhook` function.
Other functions support API interactions, data processing, and command handling.
"""
import json
import requests
import emoji
import telegram
import os
import logging
from telegram import BotCommand
from datetime import date, timedelta
import time
from typing import Optional

def get_today() -> date:
    """
    Returns the current date.
    This function is used to make testing easier by allowing it to be mocked.

    Returns:
        datetime.date: The current date
    """
    today = date.today()
    print(f"get_today() returning: {today}")  # Debug print
    return today

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
CRYPTO_NAME_MAP = {
    'BTC': 'Bitcoin',
    'ETH': 'Ethereum',
    'ADA': 'Cardano',
    'MATIC': 'Polygon',
    'SOL': 'Solana'
}
# CRYPTO_NAME_MAP: Maps cryptocurrency symbols (e.g., 'BTC') to their full names
# (e.g., 'Bitcoin') for display purposes in the /coin command output.
# Structure: {'SYMBOL': 'Full Name'}


def configure_telegram() -> telegram.Bot:
    """Configures and returns a Telegram Bot instance.

    Retrieves the Telegram Bot Token from the environment variables.

    Returns:
        telegram.Bot: An initialized Telegram Bot object.

    Raises:
        NotImplementedError: If the 'TELEGRAM_TOKEN' environment variable is not set.
    """
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

    if not TELEGRAM_TOKEN:
        logger.error('The TELEGRAM_TOKEN must be set')
        raise NotImplementedError

    return telegram.Bot(TELEGRAM_TOKEN)


def parse_and_validate_ticker_symbol(symbol: str) -> str:
    """
    Parses and validates a ticker symbol.
    Parses a ticker symbol, removes optional '$' prefix, and validates its existence
    using the Polygon API.

    Args:
        symbol (str): The ticker symbol to parse and validate (e.g., "$AAPL" or "GOOG").
            The `original_symbol` parameter name was updated to `symbol` by a previous step,
            this docstring reflects the code's current parameter name.

    Returns:
        str: The validated and processed ticker symbol (e.g., "AAPL" or "GOOG").

    Raises:
        ValueError: If the POLYGON_API_KEY is not set, if the ticker symbol is
            not found or invalid, or if there's a network error or invalid
            response format from the Polygon API.
    """
    if not POLYGON_API_KEY:
        logging.error("POLYGON_API_KEY is not set. Cannot validate ticker.")
        raise ValueError("API key for market data is not configured.")

    original_symbol_for_error_msg = symbol # Keep original for error messages
    if symbol.startswith('$'):
        symbol = symbol[1:]

    ticker_url = f'https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={POLYGON_API_KEY}'
    try:
        response = requests.get(ticker_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        response_dict = response.json()

        if response_dict.get('status') == 'NOT_FOUND' or response_dict.get('results') is None:
            raise ValueError(f"Ticker symbol '{original_symbol_for_error_msg}' not found or invalid.")
        return symbol  # Return the processed symbol (without '$')
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while validating ticker '{original_symbol_for_error_msg}' at {ticker_url}: {e}")
        raise ValueError(f"Network error while validating ticker {original_symbol_for_error_msg}.")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response for ticker '{original_symbol_for_error_msg}' from {ticker_url}: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
        raise ValueError(f"Invalid response format while validating ticker {original_symbol_for_error_msg}.")


def implied_market_status(status_date_str: str) -> bool:
    """Checks if the stock market was open on a given date.

    Uses the Polygon API with AAPL as a proxy ticker to determine market status.
    This is primarily used to find valid trading days, skipping weekends and holidays.

    Args:
        status_date_str (str): The date to check, in 'YYYY-MM-DD' format.

    Returns:
        bool: True if the market was likely open, False otherwise (e.g., weekend,
            holiday, API error, or API key not set).
    """
    print(f"Checking market status for date: {status_date_str}")  # Debug print
    if not POLYGON_API_KEY:
        logging.error("POLYGON_API_KEY is not set. Cannot check market status.")
        return False

    get_implied_market_status_url = f'https://api.polygon.io/v1/open-close/AAPL/{status_date_str}?adjusted=true&apiKey={POLYGON_API_KEY}'
    try:
        response = requests.get(get_implied_market_status_url)
        response.raise_for_status()
        response_dict = response.json()

        # Polygon API returns status "OK" and a 'from' field for open market days.
        # It returns status "NOT_FOUND" for dates where no data exists (e.g., far future, some holidays/weekends)
        # It can also return other statuses like "DELAYED" for recent data if not on a paid plan.
        # For simplicity here, we primarily check 'status' and existence of 'open'.
        if response_dict.get('status') == 'OK' and 'open' in response_dict:
            return True
        elif response_dict.get('status') == 'NOT_FOUND':
            logging.info(f"Market status for {status_date_str} (AAPL) is 'NOT_FOUND'. Assuming market closed.")
            return False
        else:
            # Handles cases like DELAYED or other unexpected statuses, assuming market might not be reliably "open" for our purposes.
            logging.warning(f"Unexpected status for {status_date_str} (AAPL): {response_dict.get('status')}. Market assumed closed. Response: {response_dict}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while checking market status for date '{status_date_str}' at {get_implied_market_status_url}: {e}")
        return False
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON response for market status check on '{status_date_str}' from {get_implied_market_status_url}: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
        return False
    except KeyError as e:
        logging.error(f"Unexpected response structure for market status check on '{status_date_str}' from {get_implied_market_status_url}: Missing key {e}. Response: {response_dict if 'response_dict' in locals() else 'N/A'}")
        return False


def first_trading_date():
    """
    Finds the first trading date of the current calendar year.

    It iterates forward from January 1st of the current year, using
    `implied_market_status` to identify a weekday when the market was open.
    Skips weekends and holidays.

    Returns:
        datetime.date: The first trading date of the current year. Returns None
                       if a trading date cannot be determined (should ideally not happen
                       in a normal year).
    """
    today = get_today()
    current_date = date(today.year, 1, 1)
    # Safety break to prevent infinite loops in unexpected scenarios, e.g., if API always fails.
    for _ in range(366): # Max days in a year + a bit
        weekday = current_date.weekday()
        # Check if it's a weekday (Monday=0 to Friday=4)
        if weekday < 5:  # 0-4 are Mon-Fri
            if implied_market_status(current_date.strftime('%Y-%m-%d')):
                return current_date  # Found a valid trading day
            else:
                # It's a weekday, but market is closed (holiday or API issue)
                current_date += timedelta(days=1)
        elif weekday == 5:  # Saturday
            current_date += timedelta(days=2)  # Skip to Monday
        else:  # Sunday (weekday == 6)
            current_date += timedelta(days=1)  # Skip to Monday

        # Ensure we don't go past a reasonable limit for the current year
        if current_date.year > today.year:
            logging.error(f"Failed to find first trading day; iteration moved to next year ({current_date}).")
            return None # Should not happen in a normal year

    logging.error("Failed to find the first trading date after extensive iteration.")
    return None # Fallback, should not be reached.


def last_trading_date() -> Optional[date]:
    """
    Finds the most recent trading date.

    It starts from today and moves backward, skipping weekends and holidays,
    using `implied_market_status` to check if the market was open.

    Returns:
        datetime.date: The most recent trading date. Returns None if a trading
                       date cannot be determined (e.g., persistent API failure).
    """
    current_date = get_today()
    # Safety break: check back up to ~2 weeks. If no trading day found, something is wrong.
    for _ in range(14):  # Check up to 14 days back
        weekday = current_date.weekday()
        if weekday < 5:  # Monday to Friday
            if implied_market_status(current_date.strftime('%Y-%m-%d')):
                return current_date  # Found a valid trading day
            else:
                # Weekday, but market closed (holiday or API issue)
                current_date -= timedelta(days=1)  # CORRECTED: Decrement
        elif weekday == 5:  # Saturday
            current_date -= timedelta(days=1)  # CORRECTED: Go to Friday (decrement)
        else:  # Sunday (weekday == 6)
            current_date -= timedelta(days=2)  # CORRECTED: Go to Friday (decrement)

    logging.error("Failed to find the last trading date after 14 attempts.")
    return None  # Fallback if no trading day is found within the loop


def ytd(original_symbol: str) -> str:
    """Calculates the Year-To-Date (YTD) performance of a given stock symbol.

    It fetches the opening price on the first trading day of the current year and
    the closing price on the most recent trading day. Then, it calculates the
    percentage change.

    The symbol is validated using `parse_and_validate_ticker_symbol` within this function.

    Args:
        original_symbol (str): The stock ticker symbol as provided by the user
                               (e.g., "$AAPL" or "GOOG").

    Returns:
        str: A formatted string describing the YTD performance, including an emoji
             indicator for up/down movement and a link to Robinhood.
             Returns an error message string if data cannot be fetched,
             API key is missing, or calculations fail.
    """
    if not POLYGON_API_KEY:
        logging.error("POLYGON_API_KEY is not set. Cannot fetch YTD data.")
        return "\nAPI key for market data is not configured. Please contact bot admin.\n"

    try:
        symbol = parse_and_validate_ticker_symbol(original_symbol)
        logging.info(f'Calculating YTD for symbol: {symbol}')

        _first_trading_date_obj = first_trading_date()
        _last_trading_date_obj = last_trading_date()

        if not _first_trading_date_obj:
            logging.error(f"Could not determine first trading date for YTD calculation of {symbol}.")
            return f"\nCould not determine the first trading date of the year for {symbol.upper()}.\n"
        if not _last_trading_date_obj:
            logging.error(f"Could not determine last trading date for YTD calculation of {symbol}.")
            return f"\nCould not determine the most recent trading date for {symbol.upper()}.\n"

        _first_trading_date_str = _first_trading_date_obj.strftime('%Y-%m-%d')
        _last_trading_date_str = _last_trading_date_obj.strftime('%Y-%m-%d')

        logging.info(f'First trading day for {symbol}: {_first_trading_date_str}')
        logging.info(f'Last trading day for {symbol}: {_last_trading_date_str}')

        def fetch_with_retry(url: str, symbol_for_log: str, date_for_log: str, key_to_extract: str) -> Optional[float]:
            """Fetches data from a URL with retries and extracts a specific key.

            Args:
                url (str): The URL to fetch data from.
                symbol_for_log (str): The ticker symbol, for logging purposes.
                date_for_log (str): The date associated with the data, for logging.
                key_to_extract (str): The key to extract from the JSON response's 'data' field.
                                      (Correction: based on ytd usage, it's directly from response dict)

            Returns:
                float | None: The extracted data as a float if successful, otherwise None.
            """
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(url)
                    response.raise_for_status() 
                    data = response.json()
                    if data.get('status') == 'OK' and key_to_extract in data:
                        return data[key_to_extract]
                    elif key_to_extract in data and data.get('status') != 'NOT_FOUND':
                         logging.warning(f"Attempt {attempt + 1}/{max_retries}: API status is '{data.get('status')}' but '{key_to_extract}' found for {symbol_for_log} on {date_for_log}. Proceeding with data.")
                         return data[key_to_extract]
                    else:
                        logging.warning(f"Attempt {attempt + 1}/{max_retries}: API status '{data.get('status')}' or '{key_to_extract}' missing for {symbol_for_log} on {date_for_log}. Message: {data.get('message')}")
                except requests.exceptions.RequestException as e:
                    logging.warning(f"Attempt {attempt + 1}/{max_retries}: Request failed for {symbol_for_log} on {date_for_log} ({url}). Error: {e}")
                except json.JSONDecodeError as e:
                    logging.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to decode JSON for {symbol_for_log} on {date_for_log} ({url}). Error: {e}, Response text: {response.text if 'response' in locals() else 'N/A'}")

                if attempt < max_retries - 1:
                    time.sleep(1) 

            logging.error(f"All {max_retries} retries failed for {symbol_for_log} on {date_for_log} at URL {url}.")
            return None

        first_day_open_url = f'https://api.polygon.io/v1/open-close/{symbol}/{_first_trading_date_str}?adjusted=true&apiKey={POLYGON_API_KEY}'
        first_day_open = fetch_with_retry(first_day_open_url, symbol, _first_trading_date_str, 'open')

        last_day_close_url = f'https://api.polygon.io/v1/open-close/{symbol}/{_last_trading_date_str}?adjusted=true&apiKey={POLYGON_API_KEY}'
        last_day_close = fetch_with_retry(last_day_close_url, symbol, _last_trading_date_str, 'close')

        if first_day_open is None or last_day_close is None:
            error_message = f"Could not retrieve pricing data for {symbol.upper()} after multiple attempts."
            logging.error(error_message + f" (first_day_open: {first_day_open}, last_day_close: {last_day_close}) for dates {_first_trading_date_str}, {_last_trading_date_str}")
            return f'\n{error_message}\n'

        try:
            first_day_open_float = float(first_day_open)
            last_day_close_float = float(last_day_close)
        except (ValueError, TypeError) as e:
            logging.error(f"Could not convert prices to float for {symbol}. Open: '{first_day_open}', Close: '{last_day_close}'. Error: {e}")
            return f"\nError processing price data for {symbol.upper()}.\n"

        if first_day_open_float == 0:
            logging.error(f"First day open price for {symbol} on {_first_trading_date_str} is 0. Cannot calculate YTD change.")
            return f"\nCannot calculate YTD for {symbol.upper()} as opening price on {_first_trading_date_str} was zero.\n"

        percent_change = ((last_day_close_float / first_day_open_float) - 1) * 100

        move = ':arrow_up_small:' if percent_change > 0 else ':arrow_down_small:'
        return emoji.emojize(
            '\n<a href="https://robinhood.com/stocks/{0}">{0}</a> is {2} {1} % this year\n'.format(symbol.upper(), format(percent_change, '.2f'), move),
            use_aliases=True)
    except ValueError as e:
        logging.warning(f"ValueError in YTD for {original_symbol}: {str(e)}")
        return f'\n{str(e)}\n'


def describe(original_symbol: str) -> str:
    """Fetches and returns a business summary for a given stock ticker symbol.

    The symbol is first validated using `parse_and_validate_ticker_symbol`.
    Then, company information is fetched from the Polygon API.

    Args:
        original_symbol (str): The stock ticker symbol as provided by the user
                               (e.g., "$AAPL" or "GOOG").

    Returns:
        str: A formatted string containing the company's name (as ticker) and
             its description. Returns an error message if the symbol is invalid,
             description is not found, API key is missing, or an API/network error occurs.
    """
    if not POLYGON_API_KEY:
        logging.error("POLYGON_API_KEY is not set. Cannot fetch description.")
        return "\nAPI key for market data is not configured. Please contact bot admin.\n"
    try:
        ticker = parse_and_validate_ticker_symbol(original_symbol)

        ticker_url = f'https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={POLYGON_API_KEY}'
        description = None
        try:
            response = requests.get(ticker_url)
            response.raise_for_status()
            response_dict = response.json()
            if response_dict.get('results') and 'description' in response_dict['results']:
                description = response_dict['results']['description']
            else:
                logging.warning(f"Description not found in API response for {ticker} from {ticker_url}. Response: {response_dict}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error while fetching description for {ticker} from {ticker_url}: {e}")
            return f"\nCould not fetch description for {ticker.upper()} due to a network issue.\n"
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response for description of {ticker} from {ticker_url}: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
            return f"\nError processing company description data for {ticker.upper()}.\n"
        except (KeyError, TypeError) as e:
            logging.warning(f"Error accessing description for {ticker} from {ticker_url}: {e}. Response: {response_dict if 'response_dict' in locals() else 'N/A'}")

        if not description:
            return f'\nNo description found for {ticker.upper()}.\n'
        else:
            return '\n<b>{0}</b>\n{1}\n'.format(ticker.upper(), description)
    except ValueError as e:
        logging.warning(f"Validation error for describe command with input '{original_symbol}': {str(e)}")
        return f'\n{str(e)}\n'


def coin() -> str:
    """Fetches current prices for major cryptocurrencies from Coinbase API.

    Retrieves prices for BTC, ETH, ADA, MATIC, SOL against USD and CAD.
    Formats the results with emojis for display.

    Returns:
        str: A string containing formatted price information for each cryptocurrency.
             If all API calls fail, returns a generic error message.
             Individual failures are noted in the output for the specific coin.
    """
    result_parts = []
    pairings_to_fetch = [
        ('BTC-USD', 'Bitcoin'), ('ETH-USD', 'Ethereum'), ('ADA-USD', 'Cardano'),
        ('MATIC-USD', 'Polygon'), ('SOL-USD', 'Solana'),
        ('BTC-CAD', 'Bitcoin'), ('ETH-CAD', 'Ethereum'), ('ADA-CAD', 'Cardano'),
        ('MATIC-CAD', 'Polygon'), ('SOL-CAD', 'Solana')
    ]

    for pairing, base_name in pairings_to_fetch:
        api_url = f'https://api.coinbase.com/v2/prices/{pairing}/spot'
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data or not isinstance(data['data'], dict):
                logging.error(f"Unexpected data structure for {pairing} from {api_url}. 'data' field missing or not a dict. Response: {data}")
                result_parts.append(f"1 {base_name} ({pairing.split('-')[1]}): Data format error")
                continue

            price_data = data['data']
            currency = price_data.get('currency')
            amount_str = price_data.get('amount')

            if not currency or amount_str is None:
                logging.error(f"Essential price data missing for {pairing} from {api_url}. Currency: '{currency}', Amount: '{amount_str}'. Response: {data}")
                result_parts.append(f"1 {base_name} ({pairing.split('-')[1]}): Data incomplete")
                continue

            try:
                amount_float = float(amount_str)
            except ValueError:
                logging.error(f"Could not convert amount '{amount_str}' to float for {pairing} from {api_url}.")
                result_parts.append(f"1 {base_name} ({currency}): Invalid price data")
                continue

            country_emoji = ':Canada:' if currency == 'CAD' else ':United_States:'
            result_parts.append(f"1 {base_name} is ${amount_float:.2f} in {country_emoji} ({currency})")

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch {pairing} from {api_url} due to network error: {e}")
            result_parts.append(f"1 {base_name} ({pairing.split('-')[1]}): Data unavailable (network)")
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON for {pairing} from {api_url}: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
            result_parts.append(f"1 {base_name} ({pairing.split('-')[1]}): Data unavailable (format)")
        except KeyError as e:
            logging.error(f"Missing expected key {e} in response for {pairing} from {api_url}. Response: {data if 'data' in locals() else 'N/A'}")
            result_parts.append(f"1 {base_name} ({pairing.split('-')[1]}): Data incomplete (missing key)")
        except Exception as e:
            logging.error(f"An unexpected error occurred processing {pairing} from {api_url}: {e}")
            result_parts.append(f"1 {base_name} ({pairing.split('-')[1]}): Error processing")

    if not result_parts:
        return emoji.emojize("Could not retrieve any cryptocurrency prices at this time. Please try again later.", use_aliases=True)

    return emoji.emojize("\n".join(result_parts), use_aliases=True)


def set_webhook(event: dict, context: object) -> dict:
    """Sets the Telegram bot webhook URL upon deployment or update.

    This function is typically triggered by an AWS CloudFormation custom resource
    or an equivalent mechanism post-deployment to register the API Gateway endpoint
    with Telegram.

    Args:
        event (dict): The event data passed to the Lambda function. Expected to
                      contain `headers.Host` and `requestContext.stage` to
                      construct the webhook URL.
        context (object): The AWS Lambda runtime context object (not used in this function).

    Returns:
        dict: A standard Lambda response object (`OK_RESPONSE` on success,
              `ERROR_RESPONSE` on failure).
    """
    logger.info('Event for set_webhook: {}'.format(event)) # Log the specific event
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
    Main handler for incoming Telegram webhook events.

    This function is triggered by API Gateway when Telegram sends an update.
    It configures the bot, sets available commands, parses the incoming message,
    routes commands to appropriate handler functions, and sends back a response.

    Args:
        event (dict): The event payload from API Gateway, containing the HTTP
                      request details, including the Telegram update in the body.
        context (object): The AWS Lambda runtime context object.

    Returns:
        dict: A standard Lambda response object (`OK_RESPONSE` after processing,
              or `ERROR_RESPONSE` if the request is not a valid POST or has no body).
    """
    bot = configure_telegram()
    logger.info('Webhook event received: {}'.format(event)) # Log the full event for debugging if needed

    # Define bot commands for Telegram's UI
    bot.setMyCommands(commands=[
        BotCommand(command='hello', description='Start interaction with the bot'),
        BotCommand(command='ytd', description='Calculates stock YTD performance (e.g., /ytd AAPL)'),
        BotCommand(command='coin', description='Get latest crypto prices (BTC, ETH, etc.)'),
        BotCommand(command='desc', description='Provides company summary (e.g., /desc TSLA)'),
        BotCommand(command='guide', description='Get help and see available commands')
    ])

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received (POST request with body)')
        try:
            update = telegram.Update.de_json(json.loads(event.get('body')), bot)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse event body as JSON: {e}")
            return ERROR_RESPONSE
        except Exception as e: # Catch other potential errors during Update creation
            logging.error(f"Error creating Telegram Update object: {e}")
            return ERROR_RESPONSE


        if not update.message or not update.message.text:
            logging.warning('Update received but no message or text content found.')
            return OK_RESPONSE # Acknowledge receipt even if no action taken

        chat_id = update.message.chat.id
        sender_name = update.message.from_user.first_name if update.message.from_user else "User"
        text = update.message.text.strip()

        command_parts = text.split(' ')
        command = command_parts[0].lower().replace('@babamuskbot', '') # Normalize command
        args = command_parts[1:]

        response_text = None

        # --- Command Handler Functions ---
        def handle_hello(sender_name: str, _args: list) -> str:
            """Handles the /hello or /start command."""
            return f"Hello {sender_name}, \nI am BabaMuskBot, your assistant for stock and crypto info!"

        def handle_ytd_prompt(_sender_name: str, _args: list) -> str:
            """Handles /ytd command when no ticker is provided."""
            return "Please provide a ticker symbol, e.g., /ytd AMZN"

        def handle_ytd_command(_sender_name: str, ytd_args: list) -> str:
            """Handles the /ytd command with a ticker symbol."""
            if not ytd_args:
                return handle_ytd_prompt(_sender_name, ytd_args) # Delegate to prompt
            if len(ytd_args) > 1:
                return "/ytd only supports 1 ticker symbol at a time."
            return ytd(ytd_args[0]) # Call main ytd function

        def handle_coin(_sender_name: str, _args: list) -> str:
            """Handles the /coin command."""
            return coin() # Call main coin function

        def handle_desc_prompt(_sender_name: str, _args: list) -> str:
            """Handles /desc command when no ticker is provided."""
            return "Please provide a ticker symbol, e.g., /desc AMZN"

        def handle_desc_command(_sender_name: str, desc_args: list) -> str:
            """Handles the /desc command with a ticker symbol."""
            if not desc_args:
                return handle_desc_prompt(_sender_name, desc_args) # Delegate to prompt
            if len(desc_args) > 1:
                return "/desc only supports 1 ticker symbol at a time."
            return describe(desc_args[0]) # Call main describe function

        def handle_guide(_sender_name: str, _args: list) -> str:
            """Handles the /guide command, displaying help information."""
            return (
                "You can use the following commands:\n"
                "/hello - Start talking to the bot\n"
                "/ytd <TICKER> - Stock YTD performance (e.g., /ytd AAPL)\n"
                "/coin - Latest crypto prices\n"
                "/desc <TICKER> - Company summary (e.g., /desc TSLA)\n"
                "/guide - Displays this help message"
            )

        command_map = {
            '/hello': handle_hello,
            '/start': handle_hello,
            '/ytd': handle_ytd_command,
            '/coin': handle_coin,
            '/desc': handle_desc_command,
            '/guide': handle_guide,
        }

        # --- Command Routing ---
        if command in command_map:
            # Special handling for prompt versions of commands if no args are provided
            if command == '/ytd' and not args:
                response_text = handle_ytd_prompt(sender_name, args)
            elif command == '/desc' and not args:
                response_text = handle_desc_prompt(sender_name, args)
            else:
                response_text = command_map[command](sender_name, args)
        else:
            if command.startswith('/'): # Log if it looked like a command but wasn't recognized
                 logging.info(f"Unrecognized command: {command} from chat_id {chat_id}")
            # No response_text means the bot won't reply to unrecognized commands or plain text.

        # --- Sending Response ---
        if response_text: # Only send a message if response_text was generated
            try:
                message = bot.sendMessage(chat_id=chat_id, text=response_text, parse_mode='HTML', disable_web_page_preview=True)
                logging.info(f'Message sent to chat_id {chat_id}. Message ID: {message.message_id}')
            except telegram.error.TelegramError as e:
                logging.error(f"Error sending message to chat_id {chat_id}: {e}")
            except Exception as e: # Catch any other unexpected errors during send
                logging.error(f"Unexpected error sending message to chat_id {chat_id}: {e}")
        else:
            logging.info(f"No response generated for command '{command}' from chat_id {chat_id}.")


        return OK_RESPONSE

    logging.warning(f"Webhook received non-POST request or request with no body: HTTP Method={event.get('httpMethod')}")
    return ERROR_RESPONSE
