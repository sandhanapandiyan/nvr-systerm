#!/bin/bash

# Django NVR Startup Script
# This script starts the Django-powered NVR system

echo "=================================="
echo "  Django NVR System Startup"
echo "=================================="
echo ""

# Activate virtual environment
echo "[1/4] Activating virtual environment..."
cd "/home/sandhanapandiyan/Documents/nvr design"
source venv_django/bin/activate

# Navigate to Django project
cd django_nvr

# Check if migrations are up to date
echo "[2/4] Checking database migrations..."
python manage.py migrate --check 2>/dev/null || {
    echo "Running migrations..."
    python manage.py migrate
}

# Collect static files (optional for development)
# echo "[3/4] Collecting static files..."
# python manage.py collectstatic --noinput

echo "[3/4] Starting Django development server..."
echo ""
echo "=================================="
echo "  Server Information"
echo "=================================="
echo "  URL: http://localhost:5000"
echo "  Admin: http://localhost:5000/admin"
echo "  API: http://localhost:5000/api/"
echo "=================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
echo "[4/4] Launching server..."
python manage.py runserver 0.0.0.0:5000
