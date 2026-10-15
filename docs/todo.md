# Python application logging refactor plan

## Review summary

The project already has a solid foundation:

- Custom RFC 3339 UTC timestamp formatting.
- Structured JSON logging via `StructuredFormatter`.
- Human-readable logging via `UnstructuredFormatter`.
- Relative-path variants for both formatter types.
- `logging.config.dictConfig`.
- A rotating file handler using the standard library.

However, the current configuration does not fully meet the requested behavior.

## Current gaps

### 1. Not every application message reaches the structured file logger

In `config/log.json`:

- `app` sends records to both the console and structured file.
- `app.report` sends records only to the structured file.
- The root logger sends records only to the console.
- Other application or third-party loggers may not reach the structured file.

The configuration also uses `propagate: false`, so child loggers do not flow through a common application-level handler.

### 2. Console output is not independently configurable at runtime

The console handler is hard-coded to `DEBUG`. The user can only change this by editing the JSON configuration. There is currently no:

- `--console-log-level` command-line option.
- Environment-variable override.
- Programmatic configuration argument.
- Validation of supported log levels.

### 3. Relative paths are relative to the current working directory

The formatter uses the process's current working directory as its relative-path base. That path can change depending on where the application is launched, which is especially relevant in containers, services, tests, and installed command-line applications.

### 4. The log file location is hard-coded

The file handler currently writes to `/tmp/logs/application.log`. This is convenient for the example container but not appropriate as a reusable application default. The application should allow the log path to be supplied by configuration or the environment.

### 5. The existing `report` behavior conflicts with “all messages to the console”

The example explicitly documents that `app.report` does not propagate to the console. That behavior should be removed or changed if all application messages must reach the console.

### 6. There are no tests

There is currently no test suite or test configuration. Logging behavior is particularly important to test because formatting, handler routing, propagation, and rotation can regress without obvious application failures.

### 7. Configuration is not packaged as application data

The default configuration path points to the repository's `config/log.json`. The project installation configuration only packages the Python modules, so an installed console entry point may not have access to the repository-level configuration.

## Recommended architecture

Use the standard library logging package rather than adding `structlog` or another logging framework.

The existing requirements can be met with this architecture:

```text
application logger(s)
        |
        v
common handlers
        |
        +--> structured rotating file handler
        |
        +--> human-readable console handler
```

Recommended behavior:

- The structured rotating file handler receives every application record.
- The console handler also receives every application record.
- The file handler always uses the structured JSON formatter.
- The console handler uses the existing human-readable formatter.
- The console handler has its own configurable level.
- File logging remains at a configurable minimum level, usually `DEBUG` or `INFO`.
- Application code logs through named loggers such as `app` and `app.report`.
- Child loggers propagate to the common application logger or root handlers rather than defining duplicate handlers.

For containerized deployments, structured logs on stdout/stderr are often preferable to application-managed files because Docker, Kubernetes, journald, and cloud platforms already provide collection and rotation. Retaining the rotating filesystem log is reasonable when a local audit/debug file is required, the deployment environment does not guarantee log collection, or the file is explicitly treated as a secondary sink.

A good design would make the rotating file handler configurable or optional while keeping structured console output available for external monitoring.

## Proposed implementation task list

### 1. Define the logging contract

Document the intended behavior before changing the implementation.

Decisions to make:

- Application logger namespace, likely `app`.
- Whether “all messages” means all application messages or every third-party library message.
- Default file log level.
- Default console log level.
- Default log file path.
- Maximum log file size.
- Number of retained rotated files.
- Whether file logging is mandatory or optional.
- Whether console output is human-readable or structured.

Recommended defaults:

```text
application namespace: app
file level: DEBUG or INFO
console level: INFO
file format: JSON Lines
console format: human-readable
file rotation: 10 MiB, 3–5 backups
file path: configurable, not hard-coded
```

### 2. Refactor handler routing

Update `config/log.json` so the common application logging path sends records to both handlers.

Preferred approach:

- Configure the application logger with `handlers = [console, structured_file]` and `propagate = false`.
- Allow child loggers such as `app.report` to inherit from `app`.
- Configure child loggers with no handlers and `propagate = true`.

This avoids duplicate records and ensures every `app.*` message reaches both destinations.

An alternative is to put the handlers on the root logger and allow application loggers to propagate. This also captures third-party logs, but requires more care to avoid unwanted library noise. The implementation should explicitly choose one model and document it.

### 3. Ensure the structured file receives all required records

The structured rotating handler should:

- Use `RelativeStructuredFormatter`.
- Receive all application records.
- Remain below the application logger's filtering threshold.
- Preserve exception and stack information.
- Emit one valid JSON object per line.
- Use UTF-8 encoding.
- Rotate based on size.

The current use of `RotatingFileHandler` is appropriate for size-based rotation. Add configuration for `filename`, `maxBytes`, `backupCount`, `encoding`, and `delay`.

Consider enabling `delay: true` so the file is not opened until the first record is emitted.

### 4. Make console level configurable

Add an explicit configuration mechanism, preferably with multiple layers:

1. Configuration-file default.
2. Environment-variable override.
3. Command-line override.

For example:

```text
LOG_CONSOLE_LEVEL=WARNING
```

and:

```text
python src/example.py --console-log-level WARNING
```

The command-line option should take precedence over the environment, which should take precedence over the JSON default.

Supported values should include `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. String levels are easier to use and document than numeric levels.

Important implementation detail: the logger level must not suppress records before the handler sees them. If the file should retain `DEBUG` while the console only displays `WARNING`, the application logger must allow `DEBUG` records and the console handler must perform the filtering.

### 5. Replace the hard-coded log path

Make the log file path configurable, for example through:

```text
--log-file /var/log/myapp/application.log
LOG_FILE=/var/log/myapp/application.log
```

The initialization function should accept configuration values rather than only a JSON path. Conceptually:

```python
init(
    config_path=...,
    console_level=...,
    log_file=...,
)
```

Decide whether the parent directory is created automatically, required to exist, or rejected with a clear startup error. Automatic creation is convenient but must account for permissions and security.

### 6. Make paths consistently project-relative

The current relative formatter uses `os.getcwd()`, which is not stable.

Introduce a defined project/source root, such as an explicit `project_root` passed to the formatter, a configured source root, or a stable package root derived during initialization. Use that root for both structured and unstructured relative paths.

Document behavior for:

- Files inside the project.
- Files outside the project.
- Installed packages.
- Symlinked paths.
- Different working directories.

A safe fallback may preserve absolute paths when a file cannot be made meaningfully relative.

### 7. Preserve and improve the formatter contracts

Keep the existing formatter distinction:

- `RelativeStructuredFormatter`: machine-readable JSON.
- `RelativeUnstructuredFormatter`: human-readable output.

Add tests and documentation guaranteeing:

- Timestamp is UTC.
- Timestamp has RFC 3339-compatible formatting.
- Timestamp ends in `Z`.
- Source path is relative according to the configured project root.
- Structured output is valid JSON.
- Human-readable output remains readable.
- Exception information is included.
- Stack information is included.
- Newline and quote characters are escaped correctly in JSON.
- Non-ASCII messages are preserved.

### 8. Improve initialization API and error handling

Refactor `log.init` to:

- Accept `Path` instead of converting immediately to `str`.
- Validate that the configuration file exists.
- Validate configured log levels.
- Produce clear errors for malformed JSON or invalid `dictConfig`.
- Avoid partially configured logging when initialization fails.
- Support runtime overrides without requiring callers to edit the JSON file.
- Avoid logging the initialization message before all handlers are confirmed operational.

The current initialization message uses the root logger's effective level, which may not be the effective level of `app`. Report the actual application and console configuration separately.

### 9. Decide how third-party logs are handled

Document whether external libraries should be included in the structured file and console output.

Recommended policy:

- All `app.*` records go to both handlers.
- Third-party logs are captured by the root logger at `WARNING` by default.
- Noisy libraries can be explicitly reduced.
- `disable_existing_loggers` remains `false` unless there is a deliberate reason to disable them.

If “every emitted record” includes third-party `DEBUG` messages, configure the root logger and root handlers accordingly. This can create significant noise and should be an explicit operational choice.

### 10. Remove or revise the special `app.report` routing

The current `app.report` logger is intentionally file-only. Change it if every message must be visible on the console:

- Remove dedicated handlers from `app.report`.
- Set `propagate` to `true`.
- Let it inherit the common application handlers.

If reports require a separate destination in the future, add a separate handler without preventing normal application routing.

### 11. Add a test suite

Add tests under:

```text
tests/
```

Recommended test cases:

#### Formatter tests

- RFC 3339 UTC timestamp.
- Timestamp uses `Z`.
- Structured output parses with `json.loads`.
- Required JSON fields are present.
- Relative file path is correct.
- Exception traceback is included.
- Stack information is included.
- Unicode, quotes, and newlines are encoded correctly.
- Human-readable output contains the expected fields.

#### Routing tests

- An `app` record appears in the structured file.
- The same record appears on the console.
- `app.report` appears in both destinations.
- A `DEBUG` record is retained in the file when console level is `WARNING`.
- Console `INFO` and `DEBUG` records are suppressed appropriately.
- No duplicate records are emitted due to propagation.
- Root and third-party logger behavior matches the documented policy.

#### Rotation tests

- A file rotates after exceeding `maxBytes`.
- Backup files are created.
- The configured backup count is respected.
- UTF-8 output works across rotated files.

#### Configuration tests

- Default configuration loads.
- Command-line level overrides the default.
- Environment level overrides the default.
- Command-line level takes precedence over the environment.
- Invalid log levels fail clearly.
- Missing or malformed configuration fails clearly.
- Logging works when launched from a different working directory.

### 12. Package the default configuration

The current default config is outside the Python package and may not exist after installation.

Choose one of these approaches:

- Move the default configuration into the package and load it using package resources.
- Build the configuration in Python and use the JSON file only as an optional user override.
- Explicitly include `config/log.json` as package data and resolve it through the installed package location.

The chosen approach should support the existing console script without depending on the caller's current directory.

### 13. Update the container behavior

Review:

- `tools/run.sh`
- `tools/docker/Dockerfile`

Tasks should include:

- Pass the configured log directory through an environment variable or command-line argument.
- Quote shell variables in `tools/run.sh`.
- Confirm the mounted directory matches the configured application path.
- Ensure the non-root container user can write to the log directory.
- Decide whether container deployments should primarily use structured stderr/stdout instead of a file.
- Document how operators retrieve rotated files.

For production container deployments, the preferred setup would generally be:

```text
structured JSON -> stdout/stderr -> container/platform collector
optional rotating file -> local fallback/debugging
```

### 14. Expand documentation

Update `README.md` with:

- Logging architecture.
- Structured JSON schema.
- Human-readable console format.
- Default levels.
- CLI options.
- Environment variables.
- File rotation settings.
- File location.
- Relative-path behavior.
- Container usage.
- Example JSON output.
- Example commands for reducing console verbosity.
- Guidance for external monitoring systems.

## Suggested implementation order

1. Define the logging contract and defaults.
2. Refactor handler routing so all `app.*` records reach both destinations.
3. Add console-level overrides.
4. Make file path and rotation settings configurable.
5. Stabilize project-relative path handling.
6. Improve initialization validation and error reporting.
7. Add formatter, routing, and rotation tests.
8. Fix configuration packaging.
9. Update container scripts and Docker behavior.
10. Document the complete operational model.

The standard-library approach is sufficient for these requirements. A third-party structured logging library would only be necessary later if the application needs advanced features such as contextual binding, automatic correlation IDs, richer event processors, or integration with a specific observability platform.