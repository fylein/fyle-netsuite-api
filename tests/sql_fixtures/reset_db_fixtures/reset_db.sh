#!/bin/bash

echo "-------------Populating Test Database---------------"
PGPASSWORD=postgres psql -h $DB_HOST -U postgres -c "drop database test_netsuite_db";
PGPASSWORD=postgres psql -h $DB_HOST -U postgres -c "create database test_netsuite_db";
PGPASSWORD=postgres psql -h $DB_HOST -U postgres test_netsuite_db -c "\i tests/sql_fixtures/reset_db_fixtures/reset_db.sql";
echo "---------------------Testing-------------------------"
