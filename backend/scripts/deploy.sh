#!/usr/bin/env bash

set -e

echo "Running database migrations..."
docker compose run --rm migrate

echo "Migrations complete"
echo " Starting application..."
docker compose up -d
