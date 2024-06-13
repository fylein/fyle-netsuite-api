# Fyle NetSuite API
Django Rest Framework API for Fyle Netsuite Integration.


### Setup

* Download and install Docker desktop for Mac from [here.](https://www.docker.com/products/docker-desktop)

* If you're using a linux machine, please download docker according to the distrubution you're on.

* Rename docker-compose.yml.template to docker-compose.yml

    ```
    $ mv docker-compose.yml.template docker-compose.yml
    ```
  
* Setup environment variables in docker_compose.yml

    ```yaml
    environment: 
      SECRET_KEY: thisisthedjangosecretkey
      ALLOWED_HOSTS: "*"
      DEBUG: "False"
      API_URL: http://localhost:8000/api
      DATABASE_URL: postgres://postgres:postgres@db:5432/netsuite_db
      FYLE_BASE_URL: 
      FYLE_CLIENT_ID: 
      FYLE_CLIENT_SECRET: 
      FYLE_TOKEN_URI: 
      NS_CONSUMER_KEY:
      NS_CONSUMER_SECRET:
   ```
  
* Build docker images

    ```
    docker-compose build api qcluster
    ```

* Run docker containers

    ```
    docker-compose up -d db api qcluster
    ```

* The database can be accessed by this command, on password prompt type `postgres`

    ```
    docker-compose run db psql -h db -U postgres netsuite_db
    ```

* To tail the logs a service you can do
    
    ```
    docker-compose logs -f <api / qcluster>
    ```

* To stop the containers

    ```
    docker-compose stop api qcluster
    ```

* To restart any containers - `would usually be needed with qcluster after you make any code changes`

    ```
    docker-compose restart qcluster
    ```

* To run bash inside any container for purpose of debugging do

    ```
    docker-compose exec api /bin/bash
    ```
 
### Running Tests

* Add the following environment variables to setup.sh file

    ```
    export API_URL='http://localhost:8000/api'
    export FYLE_BASE_URL='<fyle_base_url>
    export FYLE_CLIENT_ID='<fyle_client_id>'
    export FYLE_CLIENT_SECRET='<fyle_client_secret>'
    export FYLE_REFRESH_TOKEN='<fyle_refresh_token>'
    export FYLE_TOKEN_URI='fyle_token_uri'
    export NS_ACCOUNT_ID='<ns_client_id>'
    ```
* Run the following commands

    ```
    docker-compose -f docker-compose-pipeline.yml build
    docker-compose -f docker-compose-pipeline.yml up -d
    docker-compose -f docker-compose-pipeline.yml exec api pytest tests/
    ```

* Run the following command to update tests SQL fixture (`tests/sql_fixtures/reset_db_fixtures/reset_db.sql`)
    ```
    docker-compose -f docker-compose-pipeline.yml exec api /bin/bash tests/sql_fixtures/migration_fixtures/create_migration.sh 
    ```

* You should see output like this

    ```
    Sravans-MacBook-Air:fyle-netsuite-api sravankumar$ pytest apps/users/tests/

    Creating test database for alias 'default'...
    System check identified no issues (0 silenced).
    ......
    ----------------------------------------------------------------------
    Ran 6 tests in 15.670s

    OK
    Destroying test database for alias 'default'...
    ```