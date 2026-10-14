#!/usr/bin/env bash

set -euo pipefail

log_dir=/tmp/logs/python-logging
mkdir -p $log_dir

image="local.registry/python-logging"
tag=$(date --utc +%Y.%-m.%-d)

exec docker run --rm \
  -v $log_dir:/tmp/logs \
  "$image:$tag" "$@"
