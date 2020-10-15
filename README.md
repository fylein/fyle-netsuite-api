# Fyle NetSuite API
Django Rest Framework API for Fyle Netsuite Integration


### Setup

* Rename setup_template.sh to setup.sh

    ```
    $ mv setup_template.sh setup.sh
    ```
  
* Setup environment variables in setup.sh

    ```bash
    # Django Settings
    export SECRET_KEY=YOUR DJANGO SECRET KEY
    export ALLOWED_HOSTS=HOSTS SEPARATED BY COMMAS
    export DEBUG=True
    
    # Database Settings
    export DB_NAME=POSTGRES DB NAME
    export DB_USER=POSTGRES DB USER
    export DB_PASSWORD=POSTGRES DB PASSWORD
    export DB_HOST=POSTGRES DB
    export DB_PORT=POSTGRES DB PORT
    
    # Fyle Settings
    export API_URL=YOUR API URL
    export FYLE_BASE_URL=FYLE BASE URL
    export FYLE_CLIENT_ID=FYLE CLIENT ID
    export FYLE_CLIENT_SECRET=FYLE CLIENT SECRET
    export FYLE_TOKEN_URI=FYLE TOKEN URI

    # Netsuite Settings
    export NS_CONSUMER_KEY=NETSUITE CONSUMER KEY
    export NS_CONSUMER_SECRET=NETSUITE CONSUMER SECRET
   ```
  
* Install the requirements

    ```
    pip install -r requirements.txt
    ```

* Run the migrations

    ```
    python manage.py migrate
    ```

* Run the development server

    ```
    bash run.sh
    ```
