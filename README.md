# Fyle NetSuite API
Django Rest Framework API for Fyle Netsuite Integration


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
    export FYLE_TEST_CLIENT_ID=<client_id>
    export FYLE_TEST_CLIENT_SECRET=<client_secret>
    export FYLE_TEST_REFRESH_TOKEN=<refresh_token>
    export TEST_USER_EMAIL=<email>
    export TEST_USER_ID=<user_id>
    ```
* Run the following command

    ```
    python manage.py test --settings=fyle_netsuite_api.tests.settings
    ``` 

* You should see output like this

    ```
    Sravans-MacBook-Air:fyle-netsuite-api sravankumar$ python manage.py test --settings=fyle_netsuite_api.tests.settings

    Creating test database for alias 'default'...
    System check identified no issues (0 silenced).
    ......
    ----------------------------------------------------------------------
    Ran 6 tests in 15.670s

    OK
    Destroying test database for alias 'default'...
    ```