#! /usr/bin/env bash

set -e
set -x 

export PYTHONPATH=$(pwd)

# Wait for database
python app/backend_pre_start.py

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Seed data
python app/initial_data.py

echo "Prestart completed!"
