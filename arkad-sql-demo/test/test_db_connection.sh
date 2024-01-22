#!/bin/bash

# Get the container ID of the running postgres service
CONTAINER_ID=$(docker ps -qf "name=postgres")

# If no container was found, exit with an error message
if [ -z "$CONTAINER_ID" ]; then
    echo "No running postgres container found."
    exit 1
fi

# PostgreSQL connection parameters
DB_NAME="demo_db"
DB_USER="demo_user"
DB_PASSWORD="demo_password"
DB_HOST="localhost" # or the appropriate host
DB_PORT="5432" # or the appropriate port

PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT * FROM StockData;"

# Start an interactive bash session on the postgres container
docker exec -it $CONTAINER_ID psql -U $DB_USER -d $DB_NAME # to enter psql

# docker exec -it $CONTAINER_ID bash # to enter bash

# Execute following commands to test db setup manually
# psql -U demo_user -l # to list all databases
# psql -U demo_user -d demo_db # to enter demo_db

# \dt                 # to list all tables
# SELECT * FROM stockdata; # to query the news table