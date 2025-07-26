#!/bin/bash

# Simple wrapper to maintain backward compatibility
# Calls the actual runner in the docker directory

cd "$(dirname "$0")/docker"
exec ./run.sh "$@" 