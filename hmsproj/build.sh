#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating cache table..."
python manage.py createcachetable

echo "Collecting static files..."
python manage.py collectstatic --no-input