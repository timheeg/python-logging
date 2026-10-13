import copy
import datetime
import json
import logging
import logging.config
import os
from typing import Any


def get_unstructured_format() -> str:
    return (
        "%(asctime)s %(levelname)s "
        "%(name)s:%(pathname)s:%(lineno)d "
        "%(message)s"
    )


class Rfc3339Formatter(logging.Formatter):
    """
    Base formatter with a fixed UTC RFC 3339 timestamp.

    The date format is intentionally not configurable. The ``datefmt``
    argument is retained on ``formatTime`` for compatibility with the
    standard logging.Formatter API, but it is deliberately ignored.
    """

    def formatTime(self, record: logging.LogRecord, datefmt=None) -> str:
        timestamp = datetime.datetime.fromtimestamp(
            record.created,
            datetime.timezone.utc,
        )

        return timestamp.isoformat(timespec="milliseconds").replace(
            "+00:00",
            "Z",
        )


class StructuredFormatter(Rfc3339Formatter):
    """
    Formatter that emits each log record as valid JSON with a fixed schema.

    The constructor intentionally accepts no format arguments. The output
    schema and timestamp format are controlled by this class.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # logging.config.dictConfig passes fmt, datefmt, and style to every
        # formatter constructor. These arguments are accepted for protocol
        # compatibility but intentionally ignored because this formatter has
        # a fixed schema and timestamp format.
        super().__init__(fmt=None, datefmt=None)

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "logger": record.name,
            "level": record.levelname,
            "pid": record.process,
            "process": record.processName,
            "thread": record.thread,
            "file": record.pathname,
            "line": record.lineno,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            data["stack"] = self.formatStack(record.stack_info)

        return json.dumps(data, ensure_ascii=False)


class UnstructuredFormatter(Rfc3339Formatter):
    """
    Formatter that emits a fixed human-readable log format.

    The constructor intentionally accepts no format arguments. The output
    format and timestamp format are controlled by this class.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # logging.config.dictConfig passes fmt, datefmt, and style to every
        # formatter constructor. These arguments are accepted for protocol
        # compatibility but intentionally ignored because this formatter has
        # a fixed output format and timestamp format.
        super().__init__(
            fmt=get_unstructured_format(),
            datefmt=None,
        )


class RelativeUnstructuredFormatter(UnstructuredFormatter):
    """
    Fixed human-readable formatter with source paths relative to the
    current working directory.

    The LogRecord is copied before changing its pathname so other handlers
    receive the original record unchanged.
    """

    def format(self, record: logging.LogRecord) -> str:
        relative_record = copy.copy(record)

        if os.path.isabs(relative_record.pathname):
            relative_record.pathname = os.path.relpath(
                relative_record.pathname,
                os.getcwd(),
            )

        return super().format(relative_record)


class RelativeStructuredFormatter(StructuredFormatter):
    """
    Fixed JSON formatter with source paths relative to the current working
    directory.

    The LogRecord is copied before changing its pathname so other handlers
    receive the original record unchanged.
    """

    def format(self, record: logging.LogRecord) -> str:
        relative_record = copy.copy(record)

        if os.path.isabs(relative_record.pathname):
            relative_record.pathname = os.path.relpath(
                relative_record.pathname,
                os.getcwd(),
            )

        return super().format(relative_record)


def init(json_file: str) -> None:
    """
    Initialize logging from a JSON dictConfig file.
    """

    with open(json_file, "r", encoding="utf-8") as file:
        configuration = json.load(file)

    logging.config.dictConfig(configuration)

    logger = logging.getLogger("app")
    logger.info(
        "Logging level set to %s",
        logging.getLevelName(
            logging.getLogger().getEffectiveLevel()
        ),
    )
