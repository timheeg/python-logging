#!/usr/bin/env bash

set -euo pipefail

# Initialize configuration
target=runtime
verbose=true

# Print usage statement and exit
usage() {
>&2 cat << EOF

Usage: $(basename "$0") [OPTIONS]

Options:
 --target     Specify the target to build. Defaults to $target.
 -q, --quiet  Suppress informational output
 -h, --help   display this help

EOF
exit 1
}

# Process command line args
if ! args=$(getopt -o qh --long target:,quiet,help -- "$@"); then
  usage
fi

eval set -- "${args}"

while :
do
  case $1 in
    --target)
      target="$2"; shift 2;;
    -q | --quiet)
      verbose=false; shift;;
    -h | --help)
      usage;;
    # end of arguments
    --)
      shift; break;;
    *)
      >&2 printf "Unsupported option: %s\n" "$1"
      usage;;
  esac
done

# Log function writes all arguments to stderr ending with a newline.
log() {
  if $verbose; then
    printf "[%s] " "$(date +'%Y-%m-%d %H:%M:%S')" >&2
    printf "%b " "$@" >&2
    printf "\n" >&2
  fi
}

if [[ $# != 0 ]]; then
  log Unsupported non-flag argument
  usage
fi

log Run the script from the project root
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd -P)
project_dir=$(cd "$script_dir/../.." &> /dev/null && pwd -P)
pushd "$project_dir" > /dev/null

log 🐋 Define base image to build from
base_repo=artifactory.nextgenfed.com/ironbank-proxy
base_image=ironbank/redhat/ubi/ubi10
base_tag=10.2

log 🐋 Define image
image="local.registry/python-logging"
tag=$(date --utc +%Y.%-m.%-d)
[[ "$target" != "runtime" ]] && image="$image/$target"

log ⚙️ Build image
docker build . \
  --file tools/docker/Dockerfile \
  --target "$target" \
  --build-arg=BASE_REPO=$base_repo \
  --build-arg=BASE_IMAGE="$base_image" \
  --build-arg=BASE_TAG="$base_tag" \
  --tag "$image:$tag"

log ✅ Success. Took ${SECONDS}s
