from unittest.mock import patch, MagicMock
from geep_shared_python.logging import log_config


@patch("geep_shared_python.logging.log_config.log_settings")
def test_get_log_level(mock_log_settings: MagicMock):
    # Arrange
    mock_log_settings.log_level = "ERROR"

    # Act
    result = log_config.get_log_level()

    # Assert
    assert (
        result == 40
    )  # 40 is the numeric value for ERROR level in Python's logging module


@patch("geep_shared_python.logging.log_config.Resource")
@patch("geep_shared_python.logging.log_config.GeepOtelLoggerProvider")
def test_get_logger_provider(mock_logger_provider: MagicMock, mock_resource: MagicMock):
    # Arrange
    service_name = "test_service"

    # Act
    result = log_config.get_logger_provider(service_name)

    # Assert
    mock_resource.create.assert_called_once_with({"service.name": service_name})
    mock_logger_provider.assert_called_once_with(
        resource=mock_resource.create.return_value, shutdown_on_exit=True
    )
    assert result == mock_logger_provider.return_value


@patch("geep_shared_python.logging.log_config.get_log_level")
@patch("geep_shared_python.logging.log_config.LoggingHandler")
def test_get_log_handler(
    mock_logging_handler: MagicMock, mock_get_log_level: MagicMock
):
    # Arrange
    mock_get_log_level.return_value = 40

    # Act
    result = log_config.get_otel_log_handler()

    # Assert
    mock_logging_handler.assert_called_once_with(level=40)
    assert result == mock_logging_handler.return_value


@patch("geep_shared_python.logging.log_config.is_geep_logging_initialised")
@patch("geep_shared_python.logging.log_config.get_otel_log_handler")
@patch("geep_shared_python.logging.log_config.initialise_logging")
@patch("geep_shared_python.logging.log_config.logging")
def test_get_logger_and_add_handler_not_initialised(
    mock_logging: MagicMock,
    mock_initialise_logging: MagicMock,
    mock_log_handler: MagicMock,
    mock_is_geep_logging_initialised: MagicMock,
):
    mock_is_geep_logging_initialised.return_value = False
    # Arrange
    service_name = "test_service"
    name = "test_name"

    # Act
    result = log_config.get_logger_and_add_handler(service_name, name)

    # Assert
    mock_is_geep_logging_initialised.assert_called_once()
    mock_initialise_logging.assert_called_once_with(service_name)
    mock_logging.getLogger.assert_called_once_with(name)
    assert result == mock_logging.getLogger.return_value


@patch("geep_shared_python.logging.log_config.is_geep_logging_initialised")
@patch("geep_shared_python.logging.log_config.get_otel_log_handler")
@patch("geep_shared_python.logging.log_config.logging")
def test_get_logger_and_add_handler_initialised(
    mock_logging: MagicMock,
    mock_log_handler: MagicMock,
    mock_is_geep_logging_initialised: MagicMock,
):
    # Arrange
    mock_is_geep_logging_initialised.return_value = True
    service_name = "test_service"
    name = "test_name"

    # Act
    result = log_config.get_logger_and_add_handler(service_name, name)

    # Assert
    mock_logging.getLogger.assert_called_once_with(name)
    assert result == mock_logging.getLogger.return_value


@patch("geep_shared_python.logging.log_config.is_geep_logging_initialised")
@patch("geep_shared_python.logging.log_config.get_log_level")
@patch("geep_shared_python.logging.log_config.get_logger_provider")
@patch("geep_shared_python.logging.log_config.set_logger_provider")
@patch("geep_shared_python.logging.log_config.GeepLogger")
@patch("geep_shared_python.logging.log_config.OTLPLogExporter")
@patch("geep_shared_python.logging.log_config.BatchLogRecordProcessor")
@patch("geep_shared_python.logging.log_config.logging")
def test_initialise_logging(
    mock_logging: MagicMock,
    mock_batch_log_record_processor: MagicMock,
    mock_otlp_log_exporter: MagicMock,
    mock_geep_logger: MagicMock,
    mock_set_logger_provider: MagicMock,
    mock_get_logger_provider: MagicMock,
    mock_get_log_level: MagicMock,
    mock_is_geep_logging_initialised: MagicMock,
):
    # Arrange
    service_name = "test_service"
    mock_get_log_level.return_value = 40
    mock_is_geep_logging_initialised.return_value = False

    # Act
    log_config.initialise_logging(service_name)

    # Assert
    mock_logging.setLoggerClass.assert_called_once_with(mock_geep_logger)
    mock_logging.basicConfig.assert_called_once()
    mock_get_logger_provider.assert_called_once_with(service_name)
    mock_set_logger_provider.assert_called_once_with(
        mock_get_logger_provider.return_value
    )
    mock_otlp_log_exporter.assert_called_once()
    mock_batch_log_record_processor.assert_called_once_with(
        mock_otlp_log_exporter.return_value
    )
    mock_get_logger_provider.return_value.add_log_record_processor.assert_called_once_with(
        mock_batch_log_record_processor.return_value
    )


@patch("geep_shared_python.logging.log_config.log_settings")
def test_get_log_level_name_lower(mock_log_settings: MagicMock):
    # Arrange
    mock_log_settings.log_level = "ERROR"

    # Act
    result = log_config.get_log_level_name_lower()

    # Assert
    assert result == "error"
