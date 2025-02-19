#!/bin/bash

# Function to check if a service is ready
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "Waiting for $service to be ready..."
    while ! nc -z $host $port; do
        sleep 1
    done
    echo "$service is ready!"
}

# Start all services using docker-compose
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
wait_for_service localhost 9200 "Elasticsearch"
wait_for_service localhost 6379 "Redis"
wait_for_service localhost 9092 "Kafka"

# Initialize Kafka topics
echo "Initializing Kafka topics..."
docker-compose exec kafka /scripts/init_kafka.sh

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the crawler
echo "Starting crawler..."
python -m crawler.main --seed-urls seed_urls.json --num-workers 5

# Note: The crawler will run in the foreground. Press Ctrl+C to stop.
# The script will handle cleanup on exit
cleanup() {
    echo "Stopping crawler and cleaning up..."
    docker-compose down
    deactivate
}

trap cleanup EXIT 