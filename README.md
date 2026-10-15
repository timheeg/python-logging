# 🐍🔊 Python logging

Run `tools/docker/build.sh` to build image.

Run `tools/run.sh` to run example in container image.

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

The example writes all `app` logger records to a rotating JSON log file and
to a human-readable console handler. The console defaults to `INFO`, while
the file handler retains `DEBUG` records.

Reduce console output with either the command line or environment variable:

```text
python3 src/example.py --console-log-level WARNING
LOG_CONSOLE_LEVEL=ERROR python3 src/example.py
```

The command-line option takes precedence over `LOG_CONSOLE_LEVEL`. Override
the file destination with `--log-file` or `LOG_FILE`:

```text
python3 src/example.py --log-file /var/log/example/application.log
```

The structured file uses the standard-library `RotatingFileHandler`, with a
10 MiB maximum size and three backup files by default. Structured records
contain RFC 3339 UTC timestamps and source paths relative to the project
root. Console records use the existing human-readable formatter.

The default logging configuration is packaged with the installed application,
so the `python-logging-example` console script does not depend on the current
working directory. Use `--log-config` when an external JSON configuration is
required.

The container runner mounts `/tmp/logs/python-logging` from the host and sets
`LOG_FILE` to the matching container path. Override the host directory with
`LOG_DIR`:

```text
LOG_DIR="$PWD/logs" tools/run.sh
```

The structured application log and rotated backups are written to that host
directory as `application.log`, `application.log.1`, and so on. The console
stream remains available through Docker's standard output and error capture.
