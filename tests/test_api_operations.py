import json
import logging
from typing import Any, Mapping
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from pydantic import BaseModel

from geep_shared_python.api_operations.api_operations import (
    SupportedMethods,
    api_request,
    validate_api_response,
)
from geep_shared_python.api_operations.exceptions import ApiRequestException


@pytest.fixture(autouse=True)
def mock_otel_logging():
    """Prevent external OpenTelemetry logging connections during tests."""
    with patch(
        "geep_shared_python.logging.log_config.get_logger_and_add_handler"
    ) as mock_logger:
        mock_logger.return_value = logging.getLogger("test_logger")
        yield mock_logger


class ApiReponse(BaseModel):
    """Schema for testing API response validation."""

    message: str
    status: int


class TestApiRequest:
    def test_successful_get_request(self, mock_client: MagicMock):
        """Test successful GET request handling."""
        expected_response = {"message": "success"}

        mock_response = Mock()
        mock_response.json = Mock(return_value=expected_response)
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        response = api_request("http://test.com", SupportedMethods.GET)
        assert response == expected_response
        mock_client.get.assert_called_once()

    def test_successful_post_request(self, mock_client: MagicMock):
        """Test successful POST request handling."""
        expected_response = {"message": "success"}

        mock_response = Mock()
        mock_response.json = Mock(return_value=expected_response)
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        response = api_request(
            "http://test.com", SupportedMethods.POST, {"data": "test"}
        )
        assert response == expected_response
        mock_client.post.assert_called_once()

    def test_json_decode_error(self, mock_client: MagicMock):
        """Test handling of JSON decoding errors."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "invalid json"
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response

        with pytest.raises(ApiRequestException):
            api_request("http://test.com", SupportedMethods.GET)

    def test_request_error(self, mock_client: MagicMock):
        """Test handling of network request errors."""
        mock_client.get.side_effect = httpx.RequestError(
            "Error", request=Mock(url="http://test.com")
        )

        with pytest.raises(ApiRequestException):
            api_request("http://test.com", SupportedMethods.GET)

    def test_http_status_error(self, mock_client: MagicMock):
        """Test handling of HTTP status errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(url="http://test.com"), response=mock_response
        )

        with pytest.raises(ApiRequestException):
            api_request("http://test.com", SupportedMethods.GET)


class TestValidateApiResponse:
    def test_validate_api_response_success(self):
        """Test successful API response validation."""
        data: Mapping[str, Any] = {"message": "test", "status": 200}
        validated = validate_api_response(ApiReponse, data)
        assert isinstance(validated, ApiReponse)
        assert validated.message == "test"
        assert validated.status == 200

    def test_validate_api_response_failure(self):
        """Test API response validation with incomplete data."""
        data = {"message": "test"}  # missing required field 'status'
        with pytest.raises(ValueError):
            validate_api_response(ApiReponse, data)
