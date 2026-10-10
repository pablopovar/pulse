#!/bin/sh
set -eu

python -m db.migrate up
exec "$@"
