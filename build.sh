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

# Ensure admin exists with exact password
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
username = 'admin'
email = 'admin@trendingnewsonline.org'
password = 'trending2026!secure'

user, created = User.objects.get_or_create(username=username, defaults={'email': email})
user.set_password(password)
user.is_superuser = True
user.is_staff = True
user.save()
print(f'Superuser {username} password updated successfully to trending2026!secure.')
"