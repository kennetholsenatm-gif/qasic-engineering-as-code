#!/usr/bin/env bash
# Generate requirements-docker.txt from .[app,engineering] (pip freeze). Requires Docker.
set -e
cd "$(dirname "$0")/.."
docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim bash -c \
  'apt-get update -qq && apt-get install -y -qq libgomp1 && pip install --no-cache-dir .[app,engineering] && pip freeze' \
  > requirements-docker.txt
echo "Wrote requirements-docker.txt"
