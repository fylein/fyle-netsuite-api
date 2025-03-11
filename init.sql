-- Create the main application database
CREATE DATABASE netsuite_db;

-- Create the test database
CREATE DATABASE test_netsuite_db;

-- Connect to test database and load test data
\c test_netsuite_db;

-- Load the test data
\i /docker-entrypoint-initdb.d/reset_db.sql