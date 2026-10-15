import copy
import datetime
import json
import logging
import logging.config
import os
from pathlib import Path
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
    configured project root, falling back to the current working directory.

    The LogRecord is copied before changing its pathname so other handlers
    receive the original record unchanged.
    """

    def __init__(
        self,
        *args: object,
        project_root: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else Path.cwd()
        )

    def format(self, record: logging.LogRecord) -> str:
        relative_record = copy.copy(record)

        if os.path.isabs(relative_record.pathname):
            relative_record.pathname = os.path.relpath(
                relative_record.pathname,
                self.project_root,
            )

        return super().format(relative_record)


class RelativeStructuredFormatter(StructuredFormatter):
    """
    Fixed JSON formatter with source paths relative to the configured project
    root, falling back to the current working directory.

    The LogRecord is copied before changing its pathname so other handlers
    receive the original record unchanged.
    """

    def __init__(
        self,
        *args: object,
        project_root: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else Path.cwd()
        )

    def format(self, record: logging.LogRecord) -> str:
        relative_record = copy.copy(record)

        if os.path.isabs(relative_record.pathname):
            relative_record.pathname = os.path.relpath(
                relative_record.pathname,
                self.project_root,
            )

        return super().format(relative_record)


def _parse_level(level: str | int) -> int:
    if isinstance(level, int):
        if level < 0:
            raise ValueError(f"Invalid logging level: {level}")
        return level

    parsed_level = logging.getLevelNamesMapping().get(level.upper())
    if parsed_level is None:
        raise ValueError(f"Invalid logging level: {level!r}")
    return parsed_level


def init(
    json_file: str | Path,
    *,
    console_level: str | int | None = None,
    log_file: str | Path | None = None,
    project_root: str | Path | None = None,
) -> None:
    """
    Initialize logging from a JSON dictConfig file.
    """

    config_path = Path(json_file).resolve()
    with config_path.open("r", encoding="utf-8") as file:
        configuration = json.load(file)

    configured_console_level = (
        console_level
        if console_level is not None
        else os.environ.get("LOG_CONSOLE_LEVEL")
    )
    if configured_console_level is not None:
        configuration["handlers"]["console"]["level"] = logging.getLevelName(
            _parse_level(configured_console_level)
        )

    configured_log_file = (
        log_file if log_file is not None else os.environ.get("LOG_FILE")
    )
    if configured_log_file is not None:
        configuration["handlers"]["structured_file"]["filename"] = str(
            Path(configured_log_file).expanduser()
        )

    configured_project_root = Path(
        project_root or config_path.parent.parent
    ).resolve()
    for formatter in configuration.get("formatters", {}).values():
        formatter["project_root"] = str(configured_project_root)

    structured_file = configuration["handlers"]["structured_file"]
    log_path = Path(structured_file["filename"]).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    structured_file["filename"] = str(log_path)

    logging.config.dictConfig(configuration)

    logger = logging.getLogger("app")
    logger.info(
        "Logging initialized with console level %s and file %s",
        configuration["handlers"]["console"]["level"],
        structured_file["filename"],
    )
