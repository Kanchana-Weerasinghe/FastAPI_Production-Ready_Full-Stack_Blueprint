from unittest.mock import MagicMock, patch

import structlog

from app.core.logging import REDACTED, redact_sensitive, setup_logging


@patch("app.core.logging.config")
@patch("app.core.logging.sys")
@patch("app.core.logging.structlog.configure")
def test_setup_logging_development(
    mock_configure: MagicMock,
    mock_sys: MagicMock,
    mock_config: MagicMock,
) -> None:
    """Test that StackInfoRenderer and ConsoleRenderer are configured in a development TTY environment."""
    mock_config.ENVIRONMENT = "development"
    mock_config.LOG_LEVEL = "INFO"
    mock_sys.stderr.isatty.return_value = True
    setup_logging()
    mock_configure.assert_called_once()
    kwargs = mock_configure.call_args[1]
    processors = kwargs.get("processors", [])
    console_renderer_exists = any(isinstance(p, structlog.dev.ConsoleRenderer) for p in processors)
    stack_info_renderer_exists = any(isinstance(p, structlog.processors.StackInfoRenderer) for p in processors)
    assert console_renderer_exists
    assert stack_info_renderer_exists


@patch("app.core.logging.config")
@patch("app.core.logging.sys")
@patch("app.core.logging.structlog.configure")
def test_setup_logging_production(
    mock_configure: MagicMock,
    mock_sys: MagicMock,
    mock_config: MagicMock,
) -> None:
    """Test that JSONRenderer is configured in a non-development or non-TTY environment."""
    mock_config.ENVIRONMENT = "production"
    mock_config.LOG_LEVEL = "INFO"
    mock_sys.stderr.isatty.return_value = False
    setup_logging()
    mock_configure.assert_called_once()
    kwargs = mock_configure.call_args[1]
    processors = kwargs.get("processors", [])
    json_renderer_exists = any(isinstance(p, structlog.processors.JSONRenderer) for p in processors)
    assert json_renderer_exists


def test_redact_sensitive_values() -> None:
    """Test that secrets are removed and emails masked, recursively, while the event name is kept."""
    event = {
        "event": "user@example.com signed in",
        "password": "hunter2",
        "access_token": "abc",
        "payload": {"api_key": "k", "to": "someone@example.com", "items": ["x@y.io"]},
        "count": 3,
    }
    result = redact_sensitive(None, "info", event)
    assert result["event"] == "user@example.com signed in"
    assert result["password"] == REDACTED
    assert result["access_token"] == REDACTED
    assert result["payload"] == {"api_key": REDACTED, "to": "[EMAIL]", "items": ["[EMAIL]"]}
    assert result["count"] == 3
