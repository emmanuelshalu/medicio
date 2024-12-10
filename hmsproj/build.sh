#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

# Create the staticfiles directory if it doesn't exist
mkdir -p staticfiles

echo "Resetting migrations..."
python manage.py migrate hmsapp zero

echo "Making fresh migrations..."
python manage.py makemigrations hmsapp --noinput

echo "Running all migrations..."
python manage.py migrate --noinput

echo "Creating default groups..."
python manage.py setup_roles

echo "Creating cache table..."
python manage.py createcachetable

echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# Attempt to load initial data if it exists
if [ -f "hmsproj/fixtures/initial_data.json" ]; then
    echo "Loading initial data..."
    python manage.py loaddata initial_data.json
fi

echo "Build completed!"