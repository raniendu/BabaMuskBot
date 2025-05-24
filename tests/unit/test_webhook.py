import unittest
from unittest.mock import patch, MagicMock
import json

from baba_musk_bot.app import webhook


class TestWebhook(unittest.TestCase):
    """Tests for the webhook function."""

    @patch('baba_musk_bot.app.configure_telegram')
    def test_invalid_request(self, mock_configure):
        """Test that an invalid request returns an error response."""
        # Test with a non-POST request
        event = {'httpMethod': 'GET'}
        response = webhook(event, None)
        self.assertEqual(response['statusCode'], 400)

        # Test with a POST request but no body
        event = {'httpMethod': 'POST', 'body': None}
        response = webhook(event, None)
        self.assertEqual(response['statusCode'], 400)

    @patch('baba_musk_bot.app.configure_telegram')
    def test_valid_request_no_message(self, mock_configure):
        """Test that a valid request with no message returns an OK response."""
        # Mock the bot
        mock_bot = MagicMock()
        mock_configure.return_value = mock_bot

        # Create an event with a valid body but no message
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({'update_id': 123})
        }

        response = webhook(event, None)
        self.assertEqual(response['statusCode'], 200)
        mock_bot.sendMessage.assert_not_called()

    @patch('baba_musk_bot.app.configure_telegram')
    def test_hello_command(self, mock_configure):
        """Test that the /hello command is correctly routed."""
        # Mock the bot
        mock_bot = MagicMock()
        mock_configure.return_value = mock_bot

        # Create a mock update with a /hello command
        update_json = {
            'update_id': 123,
            'message': {
                'message_id': 456,
                'from': {'id': 789, 'first_name': 'Test', 'last_name': 'User'},
                'chat': {'id': 789, 'type': 'private'},
                'date': 1614569849,
                'text': '/hello'
            }
        }

        event = {
            'httpMethod': 'POST',
            'body': json.dumps(update_json)
        }

        # Patch telegram.Update.de_json to return a mock update
        with patch('telegram.Update.de_json') as mock_de_json:
            mock_update = MagicMock()
            mock_update.message.text = '/hello'
            mock_update.message.chat.id = 789
            mock_update.message.from_user.first_name = 'Test'
            mock_de_json.return_value = mock_update

            response = webhook(event, None)

            self.assertEqual(response['statusCode'], 200)
            mock_bot.sendMessage.assert_called_once()
            # Check that the message contains the expected greeting
            args, kwargs = mock_bot.sendMessage.call_args
            self.assertIn('Hello Test', kwargs['text'])

    @patch('baba_musk_bot.app.configure_telegram')
    @patch('baba_musk_bot.app.ytd')
    def test_ytd_command(self, mock_ytd, mock_configure):
        """Test that the /ytd command is correctly routed."""
        # Mock the bot and ytd function
        mock_bot = MagicMock()
        mock_configure.return_value = mock_bot
        mock_ytd.return_value = "YTD performance for AAPL"

        # Create a mock update with a /ytd command
        update_json = {
            'update_id': 123,
            'message': {
                'message_id': 456,
                'from': {'id': 789, 'first_name': 'Test', 'last_name': 'User'},
                'chat': {'id': 789, 'type': 'private'},
                'date': 1614569849,
                'text': '/ytd AAPL'
            }
        }

        event = {
            'httpMethod': 'POST',
            'body': json.dumps(update_json)
        }

        # Patch telegram.Update.de_json to return a mock update
        with patch('telegram.Update.de_json') as mock_de_json:
            mock_update = MagicMock()
            mock_update.message.text = '/ytd AAPL'
            mock_update.message.chat.id = 789
            mock_update.message.from_user.first_name = 'Test'
            mock_de_json.return_value = mock_update

            response = webhook(event, None)

            self.assertEqual(response['statusCode'], 200)
            mock_ytd.assert_called_once_with('AAPL')
            mock_bot.sendMessage.assert_called_once()

    @patch('baba_musk_bot.app.configure_telegram')
    @patch('baba_musk_bot.app.coin')
    def test_coin_command(self, mock_coin, mock_configure):
        """Test that the /coin command is correctly routed."""
        # Mock the bot and coin function
        mock_bot = MagicMock()
        mock_configure.return_value = mock_bot
        mock_coin.return_value = "Cryptocurrency prices"

        # Create a mock update with a /coin command
        update_json = {
            'update_id': 123,
            'message': {
                'message_id': 456,
                'from': {'id': 789, 'first_name': 'Test', 'last_name': 'User'},
                'chat': {'id': 789, 'type': 'private'},
                'date': 1614569849,
                'text': '/coin'
            }
        }

        event = {
            'httpMethod': 'POST',
            'body': json.dumps(update_json)
        }

        # Patch telegram.Update.de_json to return a mock update
        with patch('telegram.Update.de_json') as mock_de_json:
            mock_update = MagicMock()
            mock_update.message.text = '/coin'
            mock_update.message.chat.id = 789
            mock_update.message.from_user.first_name = 'Test'
            mock_de_json.return_value = mock_update

            response = webhook(event, None)

            self.assertEqual(response['statusCode'], 200)
            mock_coin.assert_called_once()
            mock_bot.sendMessage.assert_called_once()

    @patch('baba_musk_bot.app.configure_telegram')
    @patch('baba_musk_bot.app.describe')
    def test_desc_command(self, mock_describe, mock_configure):
        """Test that the /desc command is correctly routed."""
        # Mock the bot and describe function
        mock_bot = MagicMock()
        mock_configure.return_value = mock_bot
        mock_describe.return_value = "Description for AAPL"

        # Create a mock update with a /desc command
        update_json = {
            'update_id': 123,
            'message': {
                'message_id': 456,
                'from': {'id': 789, 'first_name': 'Test', 'last_name': 'User'},
                'chat': {'id': 789, 'type': 'private'},
                'date': 1614569849,
                'text': '/desc AAPL'
            }
        }

        event = {
            'httpMethod': 'POST',
            'body': json.dumps(update_json)
        }

        # Patch telegram.Update.de_json to return a mock update
        with patch('telegram.Update.de_json') as mock_de_json:
            mock_update = MagicMock()
            mock_update.message.text = '/desc AAPL'
            mock_update.message.chat.id = 789
            mock_update.message.from_user.first_name = 'Test'
            mock_de_json.return_value = mock_update

            response = webhook(event, None)

            self.assertEqual(response['statusCode'], 200)
            mock_describe.assert_called_once_with('AAPL')
            mock_bot.sendMessage.assert_called_once()

    @patch('baba_musk_bot.app.configure_telegram')
    def test_unrecognized_command(self, mock_configure):
        """Test that an unrecognized command doesn't generate a response."""
        # Mock the bot
        mock_bot = MagicMock()
        mock_configure.return_value = mock_bot

        # Create a mock update with an unrecognized command
        update_json = {
            'update_id': 123,
            'message': {
                'message_id': 456,
                'from': {'id': 789, 'first_name': 'Test', 'last_name': 'User'},
                'chat': {'id': 789, 'type': 'private'},
                'date': 1614569849,
                'text': '/unknown'
            }
        }

        event = {
            'httpMethod': 'POST',
            'body': json.dumps(update_json)
        }

        # Patch telegram.Update.de_json to return a mock update
        with patch('telegram.Update.de_json') as mock_de_json:
            mock_update = MagicMock()
            mock_update.message.text = '/unknown'
            mock_update.message.chat.id = 789
            mock_update.message.from_user.first_name = 'Test'
            mock_de_json.return_value = mock_update

            response = webhook(event, None)

            self.assertEqual(response['statusCode'], 200)
            mock_bot.sendMessage.assert_not_called()


if __name__ == '__main__':
    unittest.main()
