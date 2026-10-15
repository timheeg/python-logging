import logging
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


@pytest.fixture(autouse=True)
def reset_logging():
    yield

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    for logger_name in ("app", "app.report"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)
        logger.propagate = True