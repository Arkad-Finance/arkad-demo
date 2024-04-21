#!/bin/bash

# Stop and remove the containers, networks, and volumes
echo "Stopping the current Docker Compose stack..."
docker compose down -v

echo "Stopping postgresql to free port for rerun, need password for that..."

# If there is port conflict and you are sure about stopping postgres
# sudo systemctl stop postgresql

# Rebuild the Docker images
echo "Rebuilding Docker images..."
docker compose build

# Start the Docker Compose stack in detached mode
echo "Starting the Docker Compose stack..."
docker compose up