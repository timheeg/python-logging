"""
Standalone example of configuring and using a python logger.

Run from the repository root with:

    python3 src/example.py

The default configuration is resolved relative to this file. A different
configuration can be supplied with ``--log-config``.
"""

import argparse
import logging
from pathlib import Path

import log


logger = logging.getLogger("app")
report_logger = logging.getLogger("app.report")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Example usage of logging configuration"
    )
    parser.add_argument(
        "--log-config",
        type=Path,
        default=(
            Path(__file__).resolve().parent.parent
            / "config"
            / "log.json"
        ),
        help="Path to the logging JSON configuration file",
    )
    parser.add_argument(
        "--console-log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Minimum level written to the console",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to the structured rotating log file",
    )
    return parser.parse_args()


def main(
    log_config: Path,
    console_log_level: str | None = None,
    log_file: Path | None = None,
) -> None:
    log.init(
        log_config,
        console_level=console_log_level,
        log_file=log_file,
    )

    logger.debug(
        "Debug details are enabled by the example configuration"
    )
    logger.info("Application started")
    logger.warning(
        "This is an example warning with a value: %s",
        42,
    )

    # Child application loggers propagate to the common console and file
    # handlers, so report messages are available in both destinations.
    report_logger.info("Report entry")

    try:
        raise ValueError(
            'Example failure containing "quotes" and a newline\n'
        )
    except ValueError:
        # The structured formatter includes the traceback when configured.
        logger.exception("An example operation failed")

    logger.info("Application finished")


def run() -> None:
    arguments = parse_args()
    main(
        arguments.log_config,
        arguments.console_log_level,
        arguments.log_file,
    )


if __name__ == "__main__":
    run()
