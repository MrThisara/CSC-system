#!/bin/bash

echo "Waiting for database..."
sleep 5

echo "Running migrations..."
flask db upgrade

echo "Seeding database..."
python seed.py

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 run:app