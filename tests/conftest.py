import pytest
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'baba_musk_bot'))

@pytest.fixture
def env_vars():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'TELEGRAM_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz',
        'POLYGON_API_KEY': 'test-polygon-key'
    }):
        yield