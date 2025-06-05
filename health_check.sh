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


# --- RabbitMQ Consumer check ---
# Check if the RabbitMQ consumer is running

# Extract the queue name from the command line argument or use the default to '' if not provided
QUEUE_NAME="${1:-${QUEUE_NAME:-}}"

if [ -z "$QUEUE_NAME" ]; then
    echo "QUEUE_NAME is not set"
    exit 0
fi

# Extract parts from AMQP URL
proto_removed="${RABBITMQ_URL#amqp://}"
userpass_hostport_vhost="${proto_removed%%\?*}"
userpass_hostport="${userpass_hostport_vhost%%/*}"

# Parse user, password, host and port
userpass="${userpass_hostport%@*}"
hostport="${userpass_hostport#*@}"

unset RABBITMQ_USER
unset RABBITMQ_PASS
unset RABBITMQ_HOST
unset RABBITMQ_PORT_AMQP
unset VHOST

RABBITMQ_USER="${userpass%%:*}"
RABBITMQ_PASS="${userpass#*:}"
RABBITMQ_HOST="${hostport%%:*}"
RABBITMQ_PORT_AMQP="${hostport#*:}"
RABBITMQ_PORT=15672  # Management port
VHOST="%2F"

# --- RabbitMQ Consumer check ---
# Make the API request
response=$(curl -s -w "%{http_code}" -u "$RABBITMQ_USER:$RABBITMQ_PASS" \
  "http://$RABBITMQ_HOST:$RABBITMQ_PORT/api/queues/$VHOST/$QUEUE_NAME")

# Separate response body and HTTP status code
http_status=$(echo "$response" | tail -c 4)
body=$(echo "$response" | head -c $(($(echo "$response" | wc -c) - 3)))

# Check for HTTP failure
if [ "$http_status" -ne 200 ]; then
    echo "RabbitMQ returned HTTP $http_status - queue may not exist: $QUEUE_NAME"
    exit 1
fi

# Extract the number of consumers
consumer_count=$(echo "$body" | grep -o '"consumers":[0-9]*' | cut -d ':' -f2)

# Validate consumer count is numeric
case "$consumer_count" in
    ''|*[!0-9]*)
        echo "Invalid consumer count for queue $QUEUE_NAME"
        exit 1
        ;;
esac

# Health check result
if [ "$consumer_count" -eq 0 ]; then
    echo "No consumer present on queue: $QUEUE_NAME"
    exit 1
else
    echo "Consumer present on queue: $QUEUE_NAME ($consumer_count consumers)"
    exit 0
fi

exit 0
