#!/bin/bash

# Creating the cache table
python manage.py createcachetable --database cache_db

# Run db migrations
python manage.py migrate

# Running development server
python manage.py runserver 0.0.0.0:8000
