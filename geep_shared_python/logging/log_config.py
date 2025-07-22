import logging
import re
import typing as t
from typing import Any, Optional

import click
from fastapi import FastAPI
from opentelemetry._logs import set_logger_provider  # type: ignore
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore
from opentelemetry.instrumentation.logging import LoggingInstrumentor  # type: ignore
from opentelemetry.sdk._logs import (
    LogData,
    Logger,
    LoggerProvider,
    LoggingHandler,
    LogRecord,
)
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.util.types import Attributes
from pydantic_settings import BaseSettings

from geep_shared_python.logging.tracing_utils import create_tracer


class LogSettings(BaseSettings):
    environment: str = ""
    log_level: str = "info"
    override_local_otel_logging: bool = False
    show_otel_200_requests: bool = False


class GeepLogger(logging.Logger):
    """Overriding the built-in logger to give us more fine-tuned control over the logging levels."""

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)

    def critical(self, msg: object, *args: Any, **kwargs: Any):
        """
        We don't use critical, so log as an ERROR level instead.
        FATAL is not used in Python logging.
        Every other level is as per Geep specification.
        """
        if self.isEnabledFor(logging.CRITICAL):
            self._log(logging.ERROR, msg, args, **kwargs)


class GeepOtelLogger(Logger):
    def emit(self, record: LogRecord):
        """Emits the :class:`LogData` by associating :class:`LogRecord`
        and instrumentation info.
        """

        if not self.is_valid(record):
            raise ValueError(
                "Invalid log record, missing severity_text, severity_number, body or resource."
            )

        log_data = LogData(record, self._instrumentation_scope)
        self._multi_log_record_processor.emit(log_data)

    def is_valid(self, record: LogRecord):
        is_valid = False

        if (
            record.severity_text
            and record.severity_number
            and record.body
            and record.resource
        ):
            is_valid = True

        return is_valid


class GeepOtelLoggerProvider(LoggerProvider):
    def get_logger(
        self,
        name: str,
        version: Optional[str] = None,
        schema_url: Optional[str] = None,
        attributes: Optional[Attributes] = None,
    ) -> GeepOtelLogger:
        return GeepOtelLogger(
            self._resource,
            self._multi_log_record_processor,
            InstrumentationScope(
                name,
                version,
                schema_url,
            ),
        )


class ColouredFormatter(logging.Formatter):
    # When logging locally to the console, colour
    # the log level for easier reading
    COLORS = {
        "DEBUG": "bright_white",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bright_red",
    }

    def format(self, record):  # type: ignore
        level_name = click.style(
            record.levelname, fg=self.COLORS.get(record.levelname, "white")
        )
        record.levelname = f"{level_name}:"
        return super().format(record)


class EndpointFilter(logging.Filter):
    def __init__(self, pattern: str, *args: t.Any, **kwargs: t.Any):
        super().__init__(*args, **kwargs)
        self._pattern = pattern

    def filter(self, record: logging.LogRecord) -> bool:
        if log_settings.show_otel_200_requests:
            return True
        return re.search(self._pattern, record.getMessage()) is None


def print_logger_details(logger: logging.Logger) -> None:
    """
    A utility method to print the details of the logger and its handlers.
    Useful for debugging and understanding the logging configuration.
    """
    for k, v in logging.Logger.manager.loggerDict.items():
        print("+ [%s] {%s} " % (str.ljust(k, 20), str(v.__class__)[8:-2]))
        if not isinstance(v, logging.PlaceHolder):
            for h in v.handlers:
                print("     +++", str(h.__class__)[8:-2])


def get_logger_provider(service_name: str) -> GeepOtelLoggerProvider:
    """Return the configured logger provider, a factory for creating loggers."""
    return GeepOtelLoggerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
            }
        ),
        # ensure log records are flushed on exit
        shutdown_on_exit=True,
    )


def get_log_level() -> int:
    "Get the log level from the pydantic settings object and convert it to an int."
    log_level = log_settings.log_level.upper()
    log_level = getattr(logging, log_level, logging.NOTSET)

    if log_level == logging.NOTSET:
        raise ValueError(f"Invalid log level: {log_level}")

    return log_level


def get_log_level_name_lower() -> str:
    "Get the log level from the pydantic settings object and convert it to an int."
    log_level = log_settings.log_level.lower()
    return log_level


def get_otel_log_handler() -> LoggingHandler:
    """
    Get the log handler which receives, filters, formats and emits the log records to the exporter.
    The log handler will implictly know the provider which is a global singleton.
    """
    log_level = get_log_level()
    return LoggingHandler(level=log_level)


def is_geep_logging_initialised():
    return geep_logging_initialised


def get_logger_and_add_handler(
    service_name: str, name: str | None = None
) -> logging.Logger:

    if not service_name:
        raise ValueError("A service_name is required when fetching the logger")

    """
    Use default coloured console logging if environment is set to local
    """
    if log_settings.environment == "local":
        logger = logging.getLogger(name)

        if not len(logger.handlers):
            handler = logging.StreamHandler()
            formatter = ColouredFormatter("%(asctime)s %(levelname)-18s %(message)s")
            handler.setFormatter(formatter)
            handler.addFilter(logging.Filter())
            logger.addHandler(handler)
            logger.propagate = False

        return logger

    """
    Only initialise logging once, otherwise we get warnings
    """
    if not is_geep_logging_initialised():
        initialise_logging(service_name)

    """
    https://stackoverflow.com/questions/6333916/python-logging-ensure-a-handler-is-added-only-once
    quests to getLogger() with the same name gets a reference to the same logger object.
    Consequently we don't need to add a a handler in second and subsequent calls for the same logger.
    """
    logger = logging.getLogger(name)

    """
    Now add the OTel log handler - but only if this hasn't been added already
    """
    if not len(logger.handlers):
        otel_handler = get_otel_log_handler()
        logger.addHandler(otel_handler)

    return logger


def initialise_logging(service_name: str) -> None:
    """Initialise the logging system."""
    # This function only needs to run once.
    # When modules are imported, they may run this.
    global geep_logging_initialised
    if is_geep_logging_initialised():
        return

    # We also don't want otel logging in local environment
    # unless the OVERRIDE_LOCAL_OTEL_LOGGING is set to True
    if (
        log_settings.environment == "local"
        and log_settings.override_local_otel_logging is False
    ):
        return

    try:
        LoggingInstrumentor(set_logging_format=True)
    except Exception as e:
        # no logger, so let's print this
        print(f"ERROR: Failed to instrument logging: {e}")

    try:
        _ = create_tracer(service_name)
    except Exception as e:
        # no logger, so let's print this
        print(f"ERROR: Failed to create tracer: {e}")

    # ensure our customer class is set as the global class
    logging.setLoggerClass(GeepLogger)

    # set the log level
    log_level = get_log_level()
    logging.basicConfig(
        level=log_level, format="%(asctime)s %(levelname)-18s %(message)s"
    )

    # set up the global logger provider singleton
    logger_provider = get_logger_provider(service_name)

    # set as the global logger provider
    set_logger_provider(logger_provider)

    # add the exporter (this needs to be done last)
    exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    geep_logging_initialised = True

    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)

    return


def init_fast_api_instrumentor(app: FastAPI) -> None:
    if not log_settings.environment == "local":
        try:
            FastAPIInstrumentor.instrument_app(app)  # type:ignore
        except Exception as e:
            # no logger, so let's print this
            print(f"ERROR: Failed to instrument FastAPI app: {e}")


class NoopHandler(logging.Handler):
    def emit(self, record):  # type:ignore
        pass


def get_uvicorn_log_config() -> dict[str, Any]:
    log_level = log_settings.log_level.upper()
    uvicorn_log_config = {  # type:ignore
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s %(levelprefix)s %(message)s",
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',  # noqa: E501
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "otel": {"()": LoggingHandler},
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default", "otel"],
                "level": log_level,
            },
            "uvicorn.error": {
                "handlers": ["default", "otel"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access", "otel"],
                "level": log_level,
                "propagate": False,
                "filters": [
                    "exclude_healthcheck",
                    "exclude_health",
                    "exclude_metrics",
                ],
            },
            "app": {
                "handlers": ["default", "otel"],
                "level": log_level,
                "propagate": False,
            },
        },
        "filters": {
            "exclude_healthcheck": {"()": EndpointFilter, "pattern": r"healthcheck"},
            "exclude_health": {"()": EndpointFilter, "pattern": r"health"},
            "exclude_metrics": {
                "()": EndpointFilter,
                "pattern": r'GET /metrics HTTP/1.1" 200',
            },
        },
    }

    # Turn off the OTel logging handler in local environment
    if log_settings.environment == "local":
        uvicorn_log_config["handlers"]["otel"] = {  # type: ignore
            "formatter": "default",
            "()": NoopHandler,
        }

    return uvicorn_log_config  # type:ignore


geep_logging_initialised: bool = False
log_settings = LogSettings()
