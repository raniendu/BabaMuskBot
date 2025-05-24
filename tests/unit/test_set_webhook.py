import unittest
from unittest.mock import patch, MagicMock

from baba_musk_bot.app import set_webhook


class TestSetWebhook(unittest.TestCase):
    """Tests for the set_webhook function."""

    @patch('baba_musk_bot.app.configure_telegram')
    def test_successful_webhook_setup(self, mock_configure):
        """Test that set_webhook successfully sets up a webhook."""
        # Mock the bot
        mock_bot = MagicMock()
        mock_bot.set_webhook.return_value = True
        mock_configure.return_value = mock_bot
        
        # Create a mock event
        event = {
            'headers': {'Host': 'api.example.com'},
            'requestContext': {'stage': 'prod'}
        }
        
        response = set_webhook(event, None)
        
        # Verify the webhook was set with the correct URL
        mock_bot.set_webhook.assert_called_once_with('https://api.example.com/prod/')
        self.assertEqual(response['statusCode'], 200)

    @patch('baba_musk_bot.app.configure_telegram')
    def test_failed_webhook_setup(self, mock_configure):
        """Test that set_webhook handles failures correctly."""
        # Mock the bot with a failed webhook setup
        mock_bot = MagicMock()
        mock_bot.set_webhook.return_value = False
        mock_configure.return_value = mock_bot
        
        # Create a mock event
        event = {
            'headers': {'Host': 'api.example.com'},
            'requestContext': {'stage': 'prod'}
        }
        
        response = set_webhook(event, None)
        
        # Verify the webhook was attempted and the error response was returned
        mock_bot.set_webhook.assert_called_once_with('https://api.example.com/prod/')
        self.assertEqual(response['statusCode'], 400)

    @patch('baba_musk_bot.app.configure_telegram')
    def test_different_stage_and_host(self, mock_configure):
        """Test that set_webhook works with different stage and host values."""
        # Mock the bot
        mock_bot = MagicMock()
        mock_bot.set_webhook.return_value = True
        mock_configure.return_value = mock_bot
        
        # Create a mock event with different stage and host
        event = {
            'headers': {'Host': 'api-dev.example.org'},
            'requestContext': {'stage': 'test'}
        }
        
        response = set_webhook(event, None)
        
        # Verify the webhook was set with the correct URL
        mock_bot.set_webhook.assert_called_once_with('https://api-dev.example.org/test/')
        self.assertEqual(response['statusCode'], 200)


if __name__ == '__main__':
    unittest.main()