from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_client():
    """Create a mock HTTP client for testing API requests."""
    with patch("httpx.Client") as mock:
        mock_instance = Mock()
        mock.return_value.__enter__.return_value = mock_instance
        yield mock_instance
