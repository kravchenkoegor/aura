#!/usr/bin/env bash
set -e  # Остановить выполнение при ошибке
set -o pipefail
set -u  # Трактовать необъявленные переменные как ошибку

echo "🚀 Starting entrypoint script..."

# Путь к prestart.sh
PRESTART_SCRIPT="/code/scripts/prestart.sh"

# Выполнение prestart.sh, если он существует и исполняемый
if [ -x "$PRESTART_SCRIPT" ]; then
    echo "🔧 Running prestart script: $PRESTART_SCRIPT"
    "$PRESTART_SCRIPT"
elif [ -f "$PRESTART_SCRIPT" ]; then
    echo "⚠️  Prestart script found but not executable. Fixing permissions..."
    chmod +x "$PRESTART_SCRIPT"
    "$PRESTART_SCRIPT"
else
    echo "⚠️  No prestart script found at $PRESTART_SCRIPT. Skipping."
fi

echo "✅ Prestart completed. Executing main command: $@"
exec "$@"
