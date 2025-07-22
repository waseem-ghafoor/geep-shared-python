from uuid import UUID

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError

from geep_shared_python.logging import log_config
from geep_shared_python.schemas import shared_schemas

auth_scheme = HTTPBearer()


def convert_to_uuid(ext_dialogue_id: str) -> UUID:
    try:
        ext_dialogue_id_uuid = UUID(ext_dialogue_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Dialogue ID must be a valid UUID. {ext_dialogue_id} is not.",
        )

    return ext_dialogue_id_uuid


def get_user_token_claims(
    token: HTTPAuthorizationCredentials,
) -> shared_schemas.UserTokenClaimsSchema:
    logger = log_config.get_logger_and_add_handler("geep_shared_python", "app.auth")

    try:
        decoded_token = jwt.decode(token.credentials, options={"verify_signature": False})  # type: ignore

    except Exception as e:
        logger.info(f"Token decoding failed: {e}")
        raise HTTPException(status_code=422, detail="Invalid token.")

    try:
        user_token_claims = shared_schemas.UserTokenClaimsSchema.model_validate(
            decoded_token
        )

    except ValidationError as e:
        logger.info(f"Token claims schema validation failed: {e}")
        raise HTTPException(status_code=422, detail="Invalid token.")

    return user_token_claims
