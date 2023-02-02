#!/bin/bash

# Run db migrations
python manage.py migrate

# Creating the cache table
python manage.py createcachetable --database cache_db

# Running development server
python manage.py runserver 0.0.0.0:8000
