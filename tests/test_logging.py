"""Tests for protocol-safe logging configuration."""

import logging
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oura_mcp.utils.config import LoggingConfig
from oura_mcp.utils.logging import setup_logging


def test_logging_defaults_to_stderr():
    """Fresh configurations keep stdout available for MCP JSON-RPC."""
    assert LoggingConfig().output == "stderr"


def test_stdio_transport_redirects_stdout_logging_to_stderr(capsys):
    """Legacy stdout configs cannot corrupt the stdio protocol stream."""
    setup_logging(
        LoggingConfig(level="INFO", format="text", output="stdout"),
        stdio_transport=True,
    )

    logging.getLogger("test.protocol_logging").info("server started")
    captured = capsys.readouterr()

    assert captured.out == ""
    assert "server started" in captured.err


def test_non_stdio_transport_can_still_log_to_stdout(capsys):
    """The override is limited to transports that reserve stdout."""
    setup_logging(
        LoggingConfig(level="INFO", format="text", output="stdout"),
        stdio_transport=False,
    )

    logging.getLogger("test.stdout_logging").info("server started")
    captured = capsys.readouterr()

    assert "server started" in captured.out
    assert captured.err == ""
