#!/bin/bash
echo "Run Celery worker..."
poetry run celery -A src.celery_worker worker --loglevel=info