#!/usr/bin/env bash
# exit on error
set -o errexit

# verbose output
set -x

echo "Installing dependencies..."
pip install -r requirements.txt

# Create the staticfiles directory if it doesn't exist
mkdir -p staticfiles

echo "Checking database connection..."
python << END
import sys
import psycopg2
try:
    conn = psycopg2.connect(
        dbname="dbsqlite3hms",
        user="dbsqlite3hms_user",
        password="fT3eSbYfdfWnjGpYfhIsS2Sc718qXKxq",
        host="dpg-ctc8j03tq21c73dlv280-a",
        port="5432"
    )
    conn.close()
    print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
    sys.exit(1)
END

# Force recreate DB tables
echo "Removing migrations..."
rm -f hmsapp/migrations/0*.py
rm -f hmsapp/migrations/__pycache__/*

echo "Making fresh migrations..."
python manage.py makemigrations hmsapp

echo "Show migrations status before migrate..."
python manage.py showmigrations

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Show migrations status after migrate..."
python manage.py showmigrations

echo "Creating default groups..."
python manage.py setup_roles

echo "Creating cache table..."
python manage.py createcachetable

echo "Collecting static files..."
python manage.py collectstatic --no-input --clear

# Create a superuser
echo "Creating superuser..."
python manage.py shell << END
from django.contrib.auth.models import User
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Superuser created successfully!")
    else:
        print("Superuser already exists.")
except Exception as e:
    print(f"Error creating superuser: {e}")
END

echo "Initialize database..."
python manage.py initialize_db

echo "Final migration check..."
python manage.py showmigrations

echo "Build completed!"