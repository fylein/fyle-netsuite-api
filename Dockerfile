# Pull python base image
FROM python:3.7.4-slim

# install the requirements from the requirements.txt file via git
RUN apt-get update && apt-get -y install libpq-dev gcc && apt-get install git -y --no-install-recommends

ARG CI
RUN if [ "$CI" = "ENABLED" ]; then \
        apt-get -y update; \
        apt-get install gnupg2 lsb-release  wget -y --no-install-recommends; \
        apt-cache search postgresql-15 | grep postgresql-15 \
        sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'; \
        wget --no-check-certificate --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - ; \
        apt -y update; \
        apt-get install postgresql-15 -y --no-install-recommends; \
    fi

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Installing requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt && pip install pylint-django==2.3.0


# Copy Project to the container
RUN mkdir -p /fyle-netsuite-api
COPY . /fyle-netsuite-api/
WORKDIR /fyle-netsuite-api

# Do linting checks
RUN pylint --load-plugins pylint_django --rcfile=.pylintrc apps/**.py

# Expose development port
EXPOSE 8000

# Run development server
CMD /bin/bash run.sh
