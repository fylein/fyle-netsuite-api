#!/bin/bash


# Setting environment variables
source setup.sh

# Run db migrations
python manage.py migrate

# Running development server
python manage.py runserver 0.0.0.0:8000
