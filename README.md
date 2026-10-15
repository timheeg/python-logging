# 🐍🔊 Python logging

This project demonstrates a standard-library logging configuration with two
destinations: structured JSON records in a rotating file and human-readable
records on the console. Application loggers use common handlers, so `app` and
its children, such as `app.report`, are written to both destinations.

Run `tools/docker/build.sh` to build the image, or run the example directly
with `python3 src/example.py`.

The production image is built from the `runtime` Dockerfile target. Build the
test stage, which installs the pytest test dependency and runs the suite, with:

```text
docker build \
  --file tools/docker/Dockerfile \
  --target test \
  --tag local.registry/python-logging:test \
  .
```

Run the pytest test suite with:

```text
python3 -m pip install -e '.[test]'
python3 -m pytest
```

## Logging behavior

The example writes all `app` logger records to a rotating JSON log file and to
a human-readable console handler. The root logger is configured at `DEBUG`;
the file handler retains `DEBUG` records, while the console defaults to
`INFO`. Both handlers receive child logger records through normal propagation
without duplicate application handlers.

The structured formatter emits one JSON object per line with these fields:

| Field | Description |
| --- | --- |
| `timestamp` | UTC RFC 3339 timestamp with millisecond precision |
| `logger` | Logger name, such as `app.report` |
| `level` | Level name, such as `INFO` or `ERROR` |
| `pid` | Numeric process ID |
| `process` | Process name |
| `thread` | Numeric thread ID |
| `file` | Source path relative to the configured project root |
| `line` | Source line number |
| `module` | Python module name |
| `function` | Function name |
| `message` | Rendered log message |

Exception records additionally contain `exception` with the formatted
traceback; records with stack information contain `stack`.

For example, a normal structured record looks like:

```json
{"timestamp":"2026-10-15T12:34:56.789Z","logger":"app","level":"INFO","pid":1234,"process":"MainProcess","thread":1400,"file":"src/example.py","line":64,"module":"example","function":"main","message":"Application started"}
```

Console records use the format `timestamp level logger:path:line message`, for
example:

```text
2026-10-15T12:34:56.789Z INFO app:src/example.py:64 Application started
```

Console output is written to standard error so standard output remains
available for application output and container integration.

## Configuration

The command-line option takes precedence over `LOG_CONSOLE_LEVEL`. Supported
console levels are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`.
Override the file destination with `--log-file` or `LOG_FILE`; the command-line
option also takes precedence over the environment variable:

```text
python3 src/example.py --log-file /var/log/example/application.log
```

The structured file uses the standard-library `RotatingFileHandler`, with a
10 MiB maximum size and three backup files by default. Structured records
contain RFC 3339 UTC timestamps and source paths relative to the project
root. Console records use the existing human-readable formatter. The default
file path is `/tmp/logs/application.log` unless `--log-file`, `LOG_FILE`, or a
custom JSON configuration changes it. Parent directories are created during
logging initialization.

The default logging configuration is packaged with the installed application,
so the `python-logging-example` console script does not depend on the current
working directory. Use `--log-config` when an external JSON configuration is
required. The packaged configuration is the default; `--log-config` selects an
external JSON file instead.

The relative-path base is the configured project root. It is supplied by the
initialization code from the configuration location unless a caller provides a
different root programmatically. This keeps source paths stable when the
application is launched from another working directory.

To reduce console verbosity while retaining all file records, use either:

```text
python3 src/example.py --console-log-level WARNING
LOG_CONSOLE_LEVEL=ERROR python3 src/example.py
```

Use `--help` to see the available command-line options:

```text
python3 src/example.py --help
```

The supported runtime settings are:

| Setting | Purpose | Precedence |
| --- | --- | --- |
| `--log-config` | External JSON configuration path | Over the packaged default |
| `--console-log-level` | Console minimum level | Over `LOG_CONSOLE_LEVEL` |
| `LOG_CONSOLE_LEVEL` | Console minimum level | Over the JSON default |
| `--log-file` | Structured log path | Over `LOG_FILE` |
| `LOG_FILE` | Structured log path | Over the JSON default |

The container runner mounts `/tmp/logs/python-logging` from the host and sets
`LOG_FILE` to the matching container path. Override the host directory with
`--log-dir`:

```text
tools/run.sh --log-dir "$PWD/logs"
```

The structured application log and rotated backups are written to that host
directory as `application.log`, `application.log.1`, and so on. The console
stream remains available through Docker's standard output and error capture.
For production deployments, prefer collecting the console stream with the
container platform and treat the mounted rotating JSON file as an optional
local fallback or debugging copy. If a platform requires structured container
logs, configure it to collect the file instead (or add a JSON stdout handler in
an application-specific configuration). Parse one JSON object per line and
preserve fields such as `timestamp`, `level`, `logger`, and `exception` for
filtering and alerting.
