echo "-------------Populating Test Datebase---------------"
PGPASSWORD=postgres psql -h $DB_HOST -U postgres -c "drop database test_netsuite";
PGPASSWORD=postgres psql -h $DB_HOST -U postgres -c "create database test_netsuite";
PGPASSWORD=postgres psql -h $DB_HOST -U postgres test_netsuite -c "\i 'netsuite.sql'";
echo "---------------------Testing-------------------------"
