#!/bin/bash

# Creating the cache table
python manage.py createcachetable --database cache_db

Q_CLUSTER_NAME=import python manage.py qcluster