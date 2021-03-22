#!/bin/bash

# Creating the cache table
python manage.py createcachetable --database cache_db

# Running development server
python manage.py qcluster
