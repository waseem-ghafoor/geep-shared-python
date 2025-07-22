from datetime import date, datetime
from unittest.mock import patch
from typing import Any

import logging
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError as PydanticValidationError

from geep_shared_python.schemas import shared_schemas
from geep_shared_python.auth.auth import get_user_token_claims


@pytest.fixture(autouse=True)
def mock_otel_logging():
    """Prevent external OpenTelemetry logging connections during tests."""
    with patch(
        "geep_shared_python.logging.log_config.get_logger_and_add_handler"
    ) as mock_logger:
        mock_logger.return_value = logging.getLogger("test_logger")
        yield mock_logger


def test_get_user_token_claims_valid_token():
    """Test successful retrieval of user token claims."""
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
    decoded_token: dict[str, Any] = {
        "sub": 1234567890,
        "exp": datetime(2024, 1, 1),
        "country": "UK",
        "l2Proficiency": "B2",
        "dob": date(1990, 1, 1),
        "iss": "test_issuer",
        "referringTheme": "default_theme",
    }

    with patch("jwt.decode", return_value=decoded_token), patch.object(
        shared_schemas.UserTokenClaimsSchema,
        "model_validate",
        return_value=shared_schemas.UserTokenClaimsSchema(**decoded_token),
    ):
        user_token_claims = get_user_token_claims(token)

    assert user_token_claims.eol_id == 1234567890
    assert user_token_claims.country == "UK"
    assert user_token_claims.l2_language_level == "B2"
    assert user_token_claims.date_of_birth == date(1990, 1, 1)
    assert user_token_claims.iss == "test_issuer"


def test_get_user_token_claims_invalid_token():
    """Test handling of invalid token during decoding."""
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

    with patch("jwt.decode", side_effect=Exception("Invalid token")):
        with pytest.raises(HTTPException) as excinfo:
            get_user_token_claims(token)

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail == "Invalid token."


def test_get_user_token_claims_validation_error():
    """Test handling of token validation errors."""
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
    decoded_token: dict[str, Any] = {
        "sub": 1234567890,
        "exp": datetime(2024, 1, 1),
        "country": "UK",
        "l2Proficiency": "B2",
        "dob": date(1990, 1, 1),
        "iss": "test_issuer",
        "referringTheme": "default_theme",
    }

    with patch("jwt.decode", return_value=decoded_token), patch.object(
        shared_schemas.UserTokenClaimsSchema,
        "model_validate",
        side_effect=PydanticValidationError.from_exception_data("Validation Error", []),
    ):
        with pytest.raises(HTTPException) as excinfo:
            get_user_token_claims(token)

    assert excinfo.value.status_code == 422
    assert excinfo.value.detail == "Invalid token."
