# type: ignore

import logging
from opentelemetry.sdk._logs import Logger, LogRecord, LoggerProvider
from opentelemetry.util.types import Attributes
from typing import Any, Optional
from pydantic_settings import BaseSettings

class LogSettings(BaseSettings):
    environment: str
    log_level: str

class GeepLogger(logging.Logger):
    def __init__(self, name: str, level: int = logging.NOTSET) -> None: ...
    def critical(self, msg: object, *args: Any, **kwargs: Any) -> None: ...

class GeepOtelLogger(Logger):
    def emit(self, record: LogRecord) -> None: ...
    def is_valid(self, record: LogRecord) -> bool: ...

class GeepOtelLoggerProvider(LoggerProvider):
    def get_logger(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> GeepOtelLogger: ...

def get_logger_provider(service_name: str) -> None: ...
def get_log_level() -> int: ...
def get_log_level_name_lower() -> str: ...
def get_otel_log_handler() -> logging.Handler: ...
def get_logger_and_add_handler(
    service_name: str, name: Optional[str] = None
) -> logging.Logger: ...
def get_uvicorn_log_config() -> dict[str, Any]: ...
def initialise_logging(service_name: str) -> LoggerProvider: ...

log_settings: LogSettings

logger_provider: LoggerProvider
