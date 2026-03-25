# tests/test_logging_sanitation.py
import pytest
from pathlib import Path
from src.core.image_loader import add_images_lenient
from loguru import logger
import sys


@pytest.fixture
def caplog_workaround(caplog):
    """
    Workaround to make loguru work with pytest caplog.
    Loguru doesn't use standard logging, so we need to add a handler.
    """
    # Create a handler that writes to caplog
    handler_id = logger.add(
        lambda msg: caplog.records.append(
            type('obj', (object,), {'message': msg, 'levelname': 'WARNING'})()
        ),
        level="WARNING",
        format="{message}"
    )
    
    yield caplog
    
    # Remove the handler after test
    logger.remove(handler_id)


def test_logging_does_not_expose_full_paths(tmp_path, caplog_workaround):
    """Test that logging only shows filenames, not full paths."""
    # Create test file with known path
    test_file = tmp_path / "subdir" / "test_image.png"
    test_file.parent.mkdir(parents=True)
    test_file.write_bytes(b"not an image")
    
    # Try to load (will fail and log warning)
    add_images_lenient([str(test_file)])
    
    # Get log messages
    log_messages = [record.message for record in caplog_workaround.records]
    log_text = " ".join(log_messages)
    
    # Check logs don't contain full path components
    assert "subdir" not in log_text, f"Log should not contain directory structure: \n{log_text}"
    assert str(tmp_path) not in log_text, "Log should not contain temp path"
    
    # Check logs contain filename
    assert "test_image.png" in log_text, "Log should contain filename"
