#!/usr/bin/env bash

set -euo pipefail

# Initialize configuration
log_dir=/tmp/logs/python-logging

# Print usage statement and exit
usage() {
  cat << EOF

Usage: $(basename "$0") [OPTIONS]

Options:
  --log-dir DIR  host log storage location. Defaults to $log_dir.
  -h, --help     display this help

EOF
}

# Process command line args
if ! args=$(getopt -o h --long log-dir:,help -- "$@"); then
  usage >&2
  exit 2
fi

eval set -- "${args}"

while :
do
  case $1 in
    --log-dir)
      log_dir="$2"; shift 2;;
    -h | --help)
      usage
      exit 0;;
    # end of arguments
    --)
      shift; break;;
    *)
      >&2 printf "Unsupported option: %s\n" "$1"
      usage >&2
      exit 2;;
  esac
done

mkdir -p "$log_dir"

container_log_dir=/tmp/logs/python-logging
log_file="$container_log_dir/application.log"

image="local.registry/python-logging"
tag=$(date --utc +%Y.%-m.%-d)

exec docker run --rm \
  --env "LOG_FILE=$log_file" \
  --volume "$log_dir:$container_log_dir" \
  "$image:$tag" "$@"
