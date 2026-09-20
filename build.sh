#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Creates the admin from DJANGO_SUPERUSER_* env vars; harmless if it already exists
python manage.py createsuperuser --noinput || true