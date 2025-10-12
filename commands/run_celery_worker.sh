#!/bin/bash
echo "Run Celery worker..."
PYTHONPATH=./src poetry run celery -A celery_worker worker --loglevel=info
