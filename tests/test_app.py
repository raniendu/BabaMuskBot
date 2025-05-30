import pytest
import json
import requests_mock
from datetime import date
from unittest.mock import patch, MagicMock
from freezegun import freeze_time


class TestAppFunctions:
    def test_get_today(self):
        """Test get_today function"""
        with patch('app.os.environ.get'):
            from app import get_today
            with freeze_time("2024-03-15"):
                result = get_today()
                assert result == date(2024, 3, 15)

    def test_configure_telegram_success(self):
        """Test successful telegram configuration"""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'}):
            with patch('telegram.Bot') as mock_bot:
                from app import configure_telegram
                mock_instance = MagicMock()
                mock_bot.return_value = mock_instance
                
                result = configure_telegram()
                
                mock_bot.assert_called_once_with('123456789:ABCdefGHIjklMNOpqrsTUVwxyz')
                assert result == mock_instance

    def test_configure_telegram_missing_token(self):
        """Test telegram configuration with missing token"""
        with patch.dict('os.environ', {}, clear=True):
            from app import configure_telegram
            with pytest.raises(NotImplementedError):
                configure_telegram()

    def test_parse_ticker_removes_dollar_sign(self):
        """Test ticker parsing removes dollar sign"""
        with patch('app.POLYGON_API_KEY', 'test-key'):
            with requests_mock.Mocker() as m:
                m.get(
                    'https://api.polygon.io/v3/reference/tickers/AAPL?apiKey=test-key',
                    json={'status': 'OK', 'results': {'ticker': 'AAPL'}}
                )
                
                from app import parse_and_validate_ticker_symbol
                result = parse_and_validate_ticker_symbol('$AAPL')
                assert result == 'AAPL'

    def test_implied_market_status_open(self):
        """Test market status check when open"""
        with patch('app.POLYGON_API_KEY', 'test-key'):
            with requests_mock.Mocker() as m:
                m.get(
                    'https://api.polygon.io/v1/open-close/AAPL/2024-03-15?adjusted=true&apiKey=test-key',
                    json={'status': 'OK', 'open': 150.0}
                )
                
                from app import implied_market_status
                result = implied_market_status('2024-03-15')
                assert result is True

    def test_coin_function(self):
        """Test cryptocurrency price fetching"""
        with requests_mock.Mocker() as m:
            # Mock Bitcoin USD
            m.get(
                'https://api.coinbase.com/v2/prices/BTC-USD/spot',
                json={'data': {'currency': 'USD', 'amount': '50000.00'}}
            )
            # Mock other cryptos
            crypto_pairs = ['ETH-USD', 'ADA-USD', 'MATIC-USD', 'SOL-USD', 
                           'BTC-CAD', 'ETH-CAD', 'ADA-CAD', 'MATIC-CAD', 'SOL-CAD']
            for pair in crypto_pairs:
                currency = pair.split('-')[1]
                m.get(
                    f'https://api.coinbase.com/v2/prices/{pair}/spot',
                    json={'data': {'currency': currency, 'amount': '1000.00'}}
                )
            
            from app import coin
            result = coin()
            assert 'Bitcoin is $50000.00' in result

    def test_ytd_no_api_key(self):
        """Test YTD function without API key"""
        with patch('app.POLYGON_API_KEY', None):
            from app import ytd
            result = ytd('AAPL')
            assert 'API key for market data is not configured' in result

    def test_describe_no_api_key(self):
        """Test describe function without API key"""
        with patch('app.POLYGON_API_KEY', None):
            from app import describe
            result = describe('AAPL')
            assert 'API key for market data is not configured' in result

    def test_webhook_invalid_json(self):
        """Test webhook with invalid JSON"""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'}):
            with patch('app.configure_telegram') as mock_configure:
                mock_bot = MagicMock()
                mock_configure.return_value = mock_bot
                
                from app import webhook
                event = {
                    'httpMethod': 'POST',
                    'body': 'invalid json'
                }
                
                result = webhook(event, None)
                assert result['statusCode'] == 400

    def test_webhook_no_message(self):
        """Test webhook with update but no message"""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'}):
            with patch('app.configure_telegram') as mock_configure:
                with patch('telegram.Update.de_json') as mock_update:
                    mock_bot = MagicMock()
                    mock_configure.return_value = mock_bot
                    
                    # Mock update with no message
                    mock_update_obj = MagicMock()
                    mock_update_obj.message = None
                    mock_update.return_value = mock_update_obj
                    
                    from app import webhook
                    event = {
                        'httpMethod': 'POST',
                        'body': json.dumps({'update_id': 123})
                    }
                    
                    result = webhook(event, None)
                    assert result['statusCode'] == 200

    def test_webhook_hello_command(self):
        """Test webhook hello command"""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'}):
            with patch('app.configure_telegram') as mock_configure:
                with patch('telegram.Update.de_json') as mock_update:
                    mock_bot = MagicMock()
                    mock_configure.return_value = mock_bot
                    
                    # Mock update with hello message
                    mock_update_obj = MagicMock()
                    mock_message = MagicMock()
                    mock_chat = MagicMock()
                    mock_user = MagicMock()
                    
                    mock_chat.id = 12345
                    mock_user.first_name = 'TestUser'
                    mock_message.chat = mock_chat
                    mock_message.from_user = mock_user
                    mock_message.text = '/hello'
                    mock_update_obj.message = mock_message
                    mock_update.return_value = mock_update_obj
                    
                    mock_sent_message = MagicMock()
                    mock_sent_message.message_id = 123
                    mock_bot.sendMessage.return_value = mock_sent_message
                    
                    from app import webhook
                    event = {
                        'httpMethod': 'POST',
                        'body': json.dumps({
                            'message': {
                                'chat': {'id': 12345},
                                'from': {'first_name': 'TestUser'},
                                'text': '/hello'
                            }
                        })
                    }
                    
                    result = webhook(event, None)
                    assert result['statusCode'] == 200
                    mock_bot.sendMessage.assert_called_once()

    def test_set_webhook_success(self):
        """Test successful webhook setting"""
        with patch.dict('os.environ', {'TELEGRAM_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'}):
            with patch('app.configure_telegram') as mock_configure:
                mock_bot = MagicMock()
                mock_bot.set_webhook.return_value = True
                mock_configure.return_value = mock_bot
                
                from app import set_webhook
                event = {
                    'headers': {'Host': 'api.example.com'},
                    'requestContext': {'stage': 'prod'}
                }
                
                result = set_webhook(event, None)
                
                assert result['statusCode'] == 200
                mock_bot.set_webhook.assert_called_once_with('https://api.example.com/prod/')