#!/usr/bin/env bash

set -euo pipefail

# Initialize configuration
verbose=true

# Log function writes all arguments to stderr ending with a newline.
log() {
  if $verbose; then
    printf "[%s] " "$(date +'%Y-%m-%d %H:%M:%S')" >&2
    printf "%b " "$@" >&2
    printf "\n" >&2
  fi
}

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

log ⚙️ Build image
docker build . \
  --file tools/docker/Dockerfile \
  --build-arg=BASE_REPO=$base_repo \
  --build-arg=BASE_IMAGE="$base_image" \
  --build-arg=BASE_TAG="$base_tag" \
  --tag "$image:$tag"

log ✅ Success. Took ${SECONDS}s
