echo "-------------Populating Test Datebase---------------"
PGPASSWORD=postgres psql postgres -c "drop database test_netsuite";
PGPASSWORD=postgres psql postgres -c "create database test_netsuite";
PGPASSWORD=postgres psql test_netsuite -c "\i 'netsuite.sql'";
echo "---------------------Testing-------------------------"
