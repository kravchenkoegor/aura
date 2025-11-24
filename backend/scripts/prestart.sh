#! /usr/bin/env bash

set -e
set -x 

export PYTHONPATH=$(pwd)

python app/backend_pre_start.py

docker-compose run --rm app alembic upgrade head

python app/initial_data.py
