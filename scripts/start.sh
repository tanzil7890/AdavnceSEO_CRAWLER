#!/bin/bash
set -e  # Exit on error

# Create necessary directories
mkdir -p data/{elasticsearch,postgres,redis,prometheus}
chmod 777 data/{elasticsearch,postgres,redis,prometheus}

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
wait_for_service localhost 6378 "Redis"
wait_for_service localhost 9092 "Kafka"

# Additional wait for Kafka to be fully ready
sleep 30

# Initialize Kafka topics
echo "Initializing Kafka topics..."
bash scripts/init_kafka.sh

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create seed URLs file if it doesn't exist
mkdir -p data
if [ ! -f data/seed_urls.json ]; then
    echo "Creating seed URLs file..."
    echo '[
        "https://outhad.com",
  "https://www.gener8tor.com/"
        
    ]' > data/seed_urls.json
fi

# Start the crawler with seed URLs
echo "Starting crawler..."
python -m crawler.main --seed-urls data/seed_urls.json --num-workers 5

# Create Kafka init script
echo "Creating Kafka init script..."
cat > scripts/init_kafka.sh << 'EOF'
#!/bin/bash

# Wait for Kafka to be ready
sleep 10

# Create topics
kafka-topics.sh --create --if-not-exists \
    --bootstrap-server kafka:29092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic new_urls \
    --config retention.ms=86400000

kafka-topics.sh --create --if-not-exists \
    --bootstrap-server kafka:29092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic processing_urls \
    --config retention.ms=86400000

kafka-topics.sh --create --if-not-exists \
    --bootstrap-server kafka:29092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic completed_urls \
    --config retention.ms=86400000

kafka-topics.sh --create --if-not-exists \
    --bootstrap-server kafka:29092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic failed_urls \
    --config retention.ms=86400000

echo "Kafka topics created successfully"
EOF

chmod +x scripts/init_kafka.sh

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Create seed_urls.json if it doesn't exist
if [ ! -f "seed_urls.json" ]; then
    echo '{"urls": ["https://example.com"]}' > seed_urls.json
fi

# Add after line 4
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Grafana settings
GF_SECURITY_ADMIN_USER=crawler
GF_SECURITY_ADMIN_PASSWORD=crawler123
GF_USERS_ALLOW_SIGN_UP=false

# Other settings
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6378
EOF
fi

# Cleanup function
cleanup() {
    echo "Stopping crawler and cleaning up..."
    docker-compose down
    deactivate
}

trap cleanup EXIT 