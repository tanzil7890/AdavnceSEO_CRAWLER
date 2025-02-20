#!/bin/bash

# Wait for Kafka to be fully ready
echo "Waiting for Kafka to be fully ready..."
sleep 20

# Create topics using docker-compose exec
docker-compose exec -T kafka kafka-topics \
    --create \
    --if-not-exists \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic new_urls

docker-compose exec -T kafka kafka-topics \
    --create \
    --if-not-exists \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic processing_urls

docker-compose exec -T kafka kafka-topics \
    --create \
    --if-not-exists \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic completed_urls

docker-compose exec -T kafka kafka-topics \
    --create \
    --if-not-exists \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic failed_urls

echo "Kafka topics created successfully"
