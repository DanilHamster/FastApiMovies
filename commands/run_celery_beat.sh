#!/bin/bash
echo "Run Celery Beat..."
poetry run celery -A src.celery_worker beat --loglevel=info