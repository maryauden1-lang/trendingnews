#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files (CSS, JS)
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Populate default pages and settings
python populate_pages.py

# Create production admin automatically (if it doesn't exist)
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@trendingnewsonline.org')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Trending2026!Secure')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created successfully.')
else:
    print(f'Superuser {username} already exists.')
"