#!/bin/bash


if [ -z "$RABBITMQ_URL" ]; then
  echo "RABBITMQ_URL is not provided"
  exit 1
fi

# Extract host, user, and password from the provided URL.
# Expected URL format: amqp://user:pass@host:port/vhost
RABBITMQ_HOST=$(echo "$RABBITMQ_URL" | sed -n 's|.*://.*@\(.*\):.*|\1|p')
RABBITMQ_USER=$(echo "$RABBITMQ_URL" | sed -n 's|.*://\([^:]*\):.*@.*|\1|p')
RABBITMQ_PASS=$(echo "$RABBITMQ_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

# Use the default management port (15672)
RABBITMQ_MANAGEMENT_PORT=15672

management_url="http://$RABBITMQ_HOST:$RABBITMQ_MANAGEMENT_PORT/api/overview"
echo "Using management API at $management_url"


http_response=$(curl -s -w "\n%{http_code}" -u "$RABBITMQ_USER:$RABBITMQ_PASS" "$management_url")
http_body=$(echo "$http_response" | sed '$d')
http_code=$(echo "$http_response" | tail -n1)

if [ "$http_code" -eq 200 ]; then
  if echo "$http_body" | grep -q '"management_version":'; then
    echo "RabbitMQ management API is healthy"
  else
    echo "RabbitMQ management API returned HTTP 200 but unexpected data"
    exit 1
  fi
else
  echo "Health check failed: HTTP status code $http_code"
  exit 1
fi


# Check PgBouncer connection using pg_isready
pg_isready -h pgbouncer -p 6432 -U $PGUSER -d $PGDATABASE
PGBOUNCER_STATUS=$?

if [ $PGBOUNCER_STATUS -ne 0 ]; then
    echo "PgBouncer connection failed"
    exit 1
else
    echo "PgBouncer connection is healthy"
fi

# Check direct PostgreSQL connection using pg_isready
pg_isready -h $PGHOST -p 5432 -U $PGUSER -d $PGDATABASE
POSTGRES_STATUS=$?

if [ $POSTGRES_STATUS -ne 0 ]; then
    echo "PostgreSQL connection failed"
    exit 1
else
    echo "PostgreSQL connection is healthy"
fi

exit 0
