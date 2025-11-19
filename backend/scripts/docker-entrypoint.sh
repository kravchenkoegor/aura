#!/usr/bin/env bash

set -e
set -o pipefail
set -u

echo "Starting entrypoint script..."

PRESTART_SCRIPT="/code/scripts/prestart.sh"

if [ -x "$PRESTART_SCRIPT" ]; then
    echo "Running prestart script: $PRESTART_SCRIPT"
    "$PRESTART_SCRIPT"
elif [ -f "$PRESTART_SCRIPT" ]; then
    echo "restart script found but not executable. Fixing permissions..."
    chmod +x "$PRESTART_SCRIPT"
    "$PRESTART_SCRIPT"
else
    echo "No prestart script found at $PRESTART_SCRIPT. Skipping."
fi

echo "Prestart completed. Executing main command: $@"
exec "$@"
