#!/bin/bash

# Setting value for DB Host
export DB_HOST=db

# This step will login to psql and create the fixture database
bash tests/sql_fixtures/reset_db_fixtures/reset_db.sh

# Changing the database name to the fixture database
export DATABASE_URL=postgres://postgres:postgres@db:5432/test_netsuite_db

# Running migrations on the fixture database
python manage.py migrate

# creating a dump of the new fixture
PGPASSWORD=postgres pg_dump -U postgres -h db -d test_netsuite_db > tests/sql_fixtures/reset_db_fixtures/reset_db.sql

