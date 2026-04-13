#!/usr/bin/env bash
set -o errexit

# Activate the venv Railway creates — packages are installed here
source /app/.venv/bin/activate

# No need to pip install — Railway already did it above
python manage.py collectstatic --no-input
python manage.py migrate