#!/usr/bin/env bash
set -o errexit

# Use the venv Python that Railway creates at /app/.venv
export PATH="/app/.venv/bin:$PATH"

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate