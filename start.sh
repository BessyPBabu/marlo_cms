#!/bin/bash
set -e

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Creating superuser from environment variables (if not exists) ==="
python manage.py shell << 'EOF'
import os
from accounts.models import CustomUser

email    = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

if not email or not password:
    print("DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set — skipping superuser creation.")
else:
    if CustomUser.objects.filter(email=email).exists():
        print(f"Superuser {email} already exists — skipping.")
    else:
        CustomUser.objects.create_superuser(
            email=email,
            username=username or email.split('@')[0],
            password=password,
        )
        print(f"Superuser {email} created successfully.")
EOF

echo "=== Starting gunicorn ==="
exec gunicorn marlo_cms.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120