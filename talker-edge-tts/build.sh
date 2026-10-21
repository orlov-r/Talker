#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
engine=$(docker info --format '{{.OSType}}')
if [ "$engine" != linux ]; then
    echo 'Docker must use Linux containers.' >&2
    exit 1
fi
docker build --platform linux/amd64 -t edge-tts:local "$project_dir"
