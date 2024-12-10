#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Making migrations..."
python manage.py makemigrations --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Checking migration status..."
python manage.py showmigrations

echo "Creating cache table..."
python manage.py createcachetable

echo "Collecting static files..."
python manage.py collectstatic --no-input

# If you have initial data to load, uncomment the following line
# echo "Loading initial data..."
# python manage.py loaddata initial_data.json