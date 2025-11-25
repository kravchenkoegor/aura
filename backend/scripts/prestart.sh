#! /usr/bin/env bash

set -e
set -x 

export PYTHONPATH=$(pwd)

# Wait for database
python app/backend_pre_start.py

# Run migrations only if needed (alembic will check)
echo "Checking migrations..."
alembic current || echo "No migrations yet"
alembic upgrade head || echo "Migrations already up to date or failed"

echo "Prestart completed!"
