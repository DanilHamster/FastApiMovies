#!/bin/bash
echo "Run Celery Beat..."
PYTHONPATH=./src poetry run celery -A celery_worker beat --loglevel=info