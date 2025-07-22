import enum
import json
from typing import Any, Literal, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from geep_shared_python.api_operations.exceptions import ApiRequestException
from geep_shared_python.logging import log_config

T = TypeVar("T", bound=BaseModel)


class SupportedMethods(enum.Enum):
    GET = "GET"
    POST = "POST"


async def api_request_async(
    url: str,
    method: Literal[SupportedMethods.GET, SupportedMethods.POST],
    body: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    cookies: Optional[dict[str, str]] = None,
    timeout: int = 10,
) -> dict[str, Any]:

    logger = log_config.get_logger_and_add_handler(
        "geep-shared-python", "app.api_operations"
    )

    kwargs: dict[str, dict[str, str]] = dict()
    if headers is not None:
        kwargs["headers"] = headers
    if cookies is not None:
        kwargs["cookies"] = cookies

    # Initialize response to None at the beginning
    response = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method == SupportedMethods.POST:
                logger.debug(f"POST {body} to {url}")

                response = await client.post(url, json=body, **kwargs)  # type: ignore
            else:
                response = await client.get(url, **kwargs)  # type: ignore

            response.raise_for_status()  # raise for 400/500 exceptions

            try:
                response_dict = response.json()
            except json.JSONDecodeError as e_json_method:
                logger.warning(
                    f"response.json() failed for {url}: {e_json_method}. "
                    f"Falling back to json.loads(response.text)."
                )

                response_dict = json.loads(response.text)

            return response_dict

        except json.JSONDecodeError as e:
            error_text = (
                f"JSON Decode Error, failed to decode http response for {url}: {e}"
            )
            if response is not None:
                error_text += f" (text sample: {repr(response.text[:300])})"
            logger.error(error_text)
            raise ApiRequestException(f"JSONDecodeError for {url}: {e}.")

        except httpx.RequestError as e:
            logger.error(
                f"HTTPRequestError occurred while requesting: {e.request.url!r}."
            )
            raise ApiRequestException(f"HTTP Request Error: {e}.")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTPStatusError {e.response.status_code} while requesting: {e.request.url!r}."
            )
            raise ApiRequestException(
                f"HTTPStatusError: {e.response.status_code} {e.response.text}."
            )

        except Exception as e:
            logger.error(
                f"An unknown error occurred in api_request while requesting: {e}"
            )
            raise ApiRequestException(f"An unknown url fetch exception: {e}.")


def api_request(
    url: str,
    method: Literal[SupportedMethods.GET, SupportedMethods.POST],
    body: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    cookies: Optional[dict[str, str]] = None,
    timeout: int = 10,
) -> dict[str, Any]:

    logger = log_config.get_logger_and_add_handler(
        "geep-shared-python", "app.api_operations"
    )

    kwargs: dict[str, dict[str, str]] = dict()
    if headers is not None:
        kwargs["headers"] = headers
    if cookies is not None:
        kwargs["cookies"] = cookies

    # Initialize response to None at the beginning
    response = None

    with httpx.Client(timeout=timeout) as client:
        try:
            if method == SupportedMethods.POST:
                logger.debug(f"POST {body} to {url}")

                response = client.post(url, json=body, **kwargs)  # type: ignore
            else:
                response = client.get(url, **kwargs)  # type: ignore

            response.raise_for_status()  # raise for 400/500 exceptions

            try:
                response_dict = response.json()
            except json.JSONDecodeError as e_json_method:
                logger.warning(
                    f"response.json() failed for {url}: {e_json_method}. "
                    f"Falling back to json.loads(response.text)."
                )

                response_dict = json.loads(response.text)

            return response_dict

        except json.JSONDecodeError as e:
            error_text = (
                f"JSON Decode Error, failed to decode http response for {url}: {e}"
            )
            if response is not None:
                error_text += f" (text sample: {repr(response.text[:300])})"
            logger.error(error_text)
            raise ApiRequestException(f"JSONDecodeError for {url}: {e}.")

        except httpx.RequestError as e:
            logger.error(
                f"HTTPRequestError occurred while requesting: {e.request.url!r}."
            )
            raise ApiRequestException(f"HTTP Request Error: {e}.")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTPStatusError {e.response.status_code} while requesting: {e.request.url!r}."
            )
            raise ApiRequestException(
                f"HTTPStatusError: {e.response.status_code} {e.response.text}."
            )

        except Exception as e:
            logger.error(
                f"An unknown error occurred in api_request while requesting: {e}"
            )
            raise ApiRequestException(f"An unknown url fetch exception: {e}.")


def validate_api_response(
    validator_class: Type[T],
    data: dict[str, Any],
) -> T:
    """
    Utility method to validate a response from a service using a Pydantic model.

    Args:
        validator_class: The Pydantic model to validate the response against
        data: The data to validate (response from a service)
    """

    logger = log_config.get_logger_and_add_handler(
        "geep-shared-python", "app.api_operations"
    )

    try:
        validated_data = validator_class.model_validate(data)
    except ValueError as e:
        error_message = f"Error validating response received from service: {data}: {e}"
        logger.error(error_message)
        raise ValueError(error_message)
    return validated_data
