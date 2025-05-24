import unittest
from unittest.mock import patch, MagicMock
import json
import requests
from datetime import date

from baba_musk_bot.app import (
    parse_and_validate_ticker_symbol,
    ytd,
    describe,
    coin as coin_function,
    implied_market_status,
    first_trading_date,
    last_trading_date,
    get_today
)


class TestParseAndValidateTickerSymbol(unittest.TestCase):
    """Tests for the parse_and_validate_ticker_symbol function."""

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.requests.get')
    def test_valid_ticker_symbol(self, mock_get):
        """Test that a valid ticker symbol is correctly processed."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': {'ticker': 'AAPL'}
        }
        mock_get.return_value = mock_response

        # Test with a valid ticker symbol
        result = parse_and_validate_ticker_symbol('AAPL')
        self.assertEqual(result, 'AAPL')

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.requests.get')
    def test_valid_ticker_symbol_with_dollar_sign(self, mock_get):
        """Test that a valid ticker symbol with a dollar sign is correctly processed."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': {'ticker': 'AAPL'}
        }
        mock_get.return_value = mock_response

        # Test with a valid ticker symbol with a dollar sign
        result = parse_and_validate_ticker_symbol('$AAPL')
        self.assertEqual(result, 'AAPL')

    @patch('baba_musk_bot.app.requests.get')
    def test_invalid_ticker_symbol(self, mock_get):
        """Test that an invalid ticker symbol raises a ValueError."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'NOT_FOUND',
            'results': None
        }
        mock_get.return_value = mock_response

        # Test with an invalid ticker symbol
        with self.assertRaises(ValueError):
            parse_and_validate_ticker_symbol('INVALID')

    @patch('baba_musk_bot.app.POLYGON_API_KEY', None)
    def test_missing_api_key(self):
        """Test that a missing API key raises a ValueError."""
        with self.assertRaises(ValueError):
            parse_and_validate_ticker_symbol('AAPL')


class TestYTD(unittest.TestCase):
    """Tests for the ytd function."""

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.parse_and_validate_ticker_symbol')
    @patch('baba_musk_bot.app.first_trading_date')
    @patch('baba_musk_bot.app.last_trading_date')
    @patch('baba_musk_bot.app.requests.get')
    def test_successful_ytd_calculation(self, mock_get, mock_last_date, mock_first_date, mock_validate):
        """Test a successful YTD calculation."""
        # Mock the dependencies
        mock_validate.return_value = 'AAPL'
        mock_first_date.return_value = date(2023, 1, 3)
        mock_last_date.return_value = date(2023, 3, 15)

        # Mock the API responses
        mock_response1 = MagicMock()
        mock_response1.json.return_value = {
            'status': 'OK',
            'open': 130.0
        }
        mock_response2 = MagicMock()
        mock_response2.json.return_value = {
            'status': 'OK',
            'close': 150.0
        }
        mock_get.side_effect = [mock_response1, mock_response2]

        # Test the YTD calculation
        result = ytd('AAPL')
        self.assertIn('AAPL', result)
        self.assertIn('15.38', result)  # (150/130 - 1) * 100 = 15.38%

    @patch('baba_musk_bot.app.POLYGON_API_KEY', None)
    def test_missing_api_key(self):
        """Test that a missing API key returns an error message."""
        result = ytd('AAPL')
        self.assertIn('API key for market data is not configured', result)

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.parse_and_validate_ticker_symbol')
    def test_invalid_ticker_symbol(self, mock_validate):
        """Test that an invalid ticker symbol returns an error message."""
        mock_validate.side_effect = ValueError("Ticker symbol 'INVALID' not found or invalid.")
        result = ytd('INVALID')
        self.assertIn("Ticker symbol 'INVALID' not found or invalid.", result)


class TestDescribe(unittest.TestCase):
    """Tests for the describe function."""

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.parse_and_validate_ticker_symbol')
    @patch('baba_musk_bot.app.requests.get')
    def test_successful_description(self, mock_get, mock_validate):
        """Test a successful company description retrieval."""
        # Mock the dependencies
        mock_validate.return_value = 'AAPL'

        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': {
                'description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.'
            }
        }
        mock_get.return_value = mock_response

        # Test the description retrieval
        result = describe('AAPL')
        self.assertIn('AAPL', result)
        self.assertIn('Apple Inc. designs, manufactures', result)

    @patch('baba_musk_bot.app.POLYGON_API_KEY', None)
    def test_missing_api_key(self):
        """Test that a missing API key returns an error message."""
        result = describe('AAPL')
        self.assertIn('API key for market data is not configured', result)

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.parse_and_validate_ticker_symbol')
    @patch('baba_musk_bot.app.requests.get')
    def test_no_description_found(self, mock_get, mock_validate):
        """Test that a missing description returns an error message."""
        # Mock the dependencies
        mock_validate.return_value = 'AAPL'

        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': {}  # No description field
        }
        mock_get.return_value = mock_response

        # Test the description retrieval
        result = describe('AAPL')
        self.assertIn('No description found for AAPL', result)


class TestCoin(unittest.TestCase):
    """Tests for the coin function."""

    @patch('baba_musk_bot.app.requests.get')
    def test_successful_coin_retrieval(self, mock_get):
        """Test a successful cryptocurrency price retrieval."""
        # Mock the API responses
        mock_responses = []
        for currency in ['USD', 'CAD']:
            for coin in ['BTC', 'ETH', 'ADA', 'MATIC', 'SOL']:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    'data': {
                        'base': coin,
                        'currency': currency,
                        'amount': '50000.00' if coin == 'BTC' else '2000.00'
                    }
                }
                mock_responses.append(mock_response)
        mock_get.side_effect = mock_responses

        # Test the coin retrieval
        result = coin_function()
        self.assertIn('Bitcoin', result)
        self.assertIn('Ethereum', result)
        self.assertIn('USD', result)
        self.assertIn('CAD', result)

    @patch('baba_musk_bot.app.requests.get')
    def test_partial_failure(self, mock_get):
        """Test that the function handles partial API failures gracefully."""
        # Mock some successful and some failed responses
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            'data': {
                'base': 'BTC',
                'currency': 'USD',
                'amount': '50000.00'
            }
        }
        mock_get.side_effect = [
            mock_response_success,  # First call succeeds
            requests.exceptions.RequestException("API error")  # Second call fails
        ] + [mock_response_success] * 8  # Remaining calls succeed

        # Test the coin retrieval
        result = coin_function()
        self.assertIn('Bitcoin', result)
        self.assertIn('Data unavailable', result)  # Error message for failed call


class TestMarketStatus(unittest.TestCase):
    """Tests for market status related functions."""

    @patch('baba_musk_bot.app.POLYGON_API_KEY', 'dummy_key')
    @patch('baba_musk_bot.app.requests.get')
    def test_implied_market_status_open(self, mock_get):
        """Test that implied_market_status correctly identifies an open market day."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'open': 130.0,
            'close': 150.0
        }
        mock_get.return_value = mock_response

        # Test the market status check
        result = implied_market_status('2023-03-15')
        self.assertTrue(result)

    @patch('baba_musk_bot.app.requests.get')
    def test_implied_market_status_closed(self, mock_get):
        """Test that implied_market_status correctly identifies a closed market day."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'NOT_FOUND'
        }
        mock_get.return_value = mock_response

        # Test the market status check
        result = implied_market_status('2023-03-18')  # A Saturday
        self.assertFalse(result)

    @patch('baba_musk_bot.app.get_today')
    @patch('baba_musk_bot.app.implied_market_status')
    def test_first_trading_date(self, mock_implied_status, mock_get_today):
        """Test that first_trading_date correctly finds the first trading day of the year."""
        # Mock the dependencies
        mock_get_today.return_value = date(2023, 3, 15)

        # Mock implied_market_status to return False for Jan 1-2 (weekend/holiday) and True for Jan 3
        def mock_status_side_effect(date_str):
            return date_str >= '2023-01-03'

        mock_implied_status.side_effect = mock_status_side_effect

        # Test finding the first trading date
        result = first_trading_date()
        self.assertEqual(result, date(2023, 1, 3))

    @patch('baba_musk_bot.app.get_today')
    @patch('baba_musk_bot.app.implied_market_status')
    def test_last_trading_date(self, mock_implied_status, mock_get_today):
        """Test that last_trading_date correctly finds the most recent trading day."""
        # Mock the dependencies
        mock_get_today.return_value = date(2023, 3, 18)  # A Saturday

        # Mock implied_market_status to return True for Mar 17 (Friday) and False for Mar 18 (Saturday)
        def mock_status_side_effect(date_str):
            return date_str <= '2023-03-17'

        mock_implied_status.side_effect = mock_status_side_effect

        # Test finding the last trading date
        result = last_trading_date()
        self.assertEqual(result, date(2023, 3, 17))


if __name__ == '__main__':
    unittest.main()
