import json
import logging
import logging.handlers
from pathlib import Path

import log


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGURATION = PROJECT_ROOT / "config" / "log.json"


def test_structured_formatter_outputs_json_with_relative_path() -> None:
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=str(PROJECT_ROOT / "src" / "example.py"),
        lineno=42,
        msg="message with %s",
        args=("quotes",),
        exc_info=None,
    )

    output = log.RelativeStructuredFormatter(
        project_root=str(PROJECT_ROOT)
    ).format(record)
    data = json.loads(output)

    assert data["message"] == "message with quotes"
    assert data["file"] == "src/example.py"
    assert data["timestamp"].endswith("Z")
    assert data["logger"] == "app"


def test_init_routes_app_children_to_console_and_file(
    tmp_path: Path,
    capsys,
) -> None:
    log_file = tmp_path / "nested" / "application.log"

    log.init(
        CONFIGURATION,
        console_level="INFO",
        log_file=log_file,
        project_root=PROJECT_ROOT,
    )
    logging.getLogger("app").debug("debug detail")
    logging.getLogger("app.report").info("report entry")
    logging.getLogger("app").warning("visible warning")

    console_output = capsys.readouterr().err
    records = [
        json.loads(line)
        for line in log_file.read_text(encoding="utf-8").splitlines()
    ]
    messages = [record["message"] for record in records]

    assert "debug detail" not in console_output
    assert "visible warning" in console_output
    assert "report entry" in console_output
    assert "debug detail" in messages
    assert "report entry" in messages
    assert "visible warning" in messages


def test_environment_console_level_is_used(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    log_file = tmp_path / "application.log"
    monkeypatch.setenv("LOG_CONSOLE_LEVEL", "ERROR")

    log.init(
        CONFIGURATION,
        log_file=log_file,
        project_root=PROJECT_ROOT,
    )
    logging.getLogger("app").warning("hidden warning")
    logging.getLogger("app").error("visible error")

    console_output = capsys.readouterr().err
    assert "hidden warning" not in console_output
    assert "visible error" in console_output


def test_rotating_handler_creates_backup_file(tmp_path: Path) -> None:
    log_path = tmp_path / "application.log"
    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=100,
        backupCount=1,
        encoding="utf-8",
    )
    handler.setFormatter(log.StructuredFormatter())
    logger = logging.getLogger("rotation-test")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        for index in range(10):
            logger.info("record %d with enough text to rotate", index)
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert log_path.exists()
    assert Path(f"{log_path}.1").exists()