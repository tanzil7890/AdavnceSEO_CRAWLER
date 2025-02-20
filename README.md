# Distributed Web Crawler with ML-Powered Analytics

A high-performance distributed web crawler system with machine learning capabilities for intelligent content processing, URL prioritization, and advanced analytics. The system features a modern React-based dashboard for real-time monitoring and control.

## Features

### Core Capabilities
- **Distributed Crawling**
  * Scalable URL frontier with ML-based prioritization
  * Concurrent crawling with politeness policies
  * Robust error handling and retry mechanisms
  * Configurable crawl depth and scope

### Machine Learning Components
- **Content Analysis**
  * Sentiment analysis using DistilBERT
  * Named entity extraction with BERT and spaCy
  * Topic classification using BART
  * Custom content classification with fine-tuning capabilities

- **URL Prioritization**
  * ML-powered URL scoring
  * Domain reputation analysis
  * Adaptive crawl strategies
  * Pattern-based URL evaluation

### Data Processing
- **Content Processing**
  * Advanced HTML parsing and cleaning
  * Keyword extraction and scoring
  * Link analysis and relationship mapping
  * Image and metadata extraction

### Storage System
- **Multi-Database Architecture**
  * Elasticsearch for full-text search and analytics
  * PostgreSQL for structured data and raw content
  * Redis for URL frontier and caching
  * Kafka for message queuing

### Monitoring & Analytics
- **Real-time Dashboard**
  * Modern React-based UI with Material Design
  * Live crawling statistics
  * Domain-specific analytics
  * Search functionality
  * System configuration interface

- **Metrics & Logging**
  * Prometheus integration
  * Grafana dashboards
  * Comprehensive logging
  * Performance tracking

## System Requirements

- Python 3.8+
- Node.js 14+
- Docker and Docker Compose
- 8GB RAM minimum (16GB recommended)
- 4 CPU cores minimum

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd distributed-crawler
```

### 2. Environment Setup

Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

Install Python dependencies:
```bash
pip install -r requirements.txt

# Download required NLP models
python -m spacy download en_core_web_sm
python -m nltk.downloader punkt
```

### 3. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Elasticsearch settings
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200

# PostgreSQL settings
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crawler
POSTGRES_USER=crawler
POSTGRES_PASSWORD=your_secure_password

# Other settings as needed
```

### 4. Start Infrastructure Services

Start all required services using Docker Compose:
```bash
docker-compose up -d
```

This will start:
- Elasticsearch
- PostgreSQL
- Redis
- Kafka & Zookeeper
- Prometheus
- Grafana

### 5. Setup Web Dashboard

Install frontend dependencies:
```bash
cd crawler/web/frontend
npm install
```

Start the development server:
```bash
npm start
```

The dashboard will be available at `http://localhost:3000`

### 6. Initialize the System

Run the initialization script:
```bash
./scripts/start.sh
```

This script will:
- Wait for all services to be ready
- Initialize Kafka topics
- Create necessary database schemas
- Start the crawler system

## Running the Crawler

### Start Crawling
```bash
python -m crawler.main --seed-urls seed_urls.json --num-workers 5
```

### Monitor Progress
- Access the dashboard at `http://localhost:3000`
- View metrics at `http://localhost:9090` (Prometheus)
- Check Grafana dashboards at `http://localhost:3000`

## API Endpoints

### Crawler Control
- `POST /crawl` - Add URLs to crawl
- `GET /stats` - Get crawler statistics
- `GET /domain/{domain}/stats` - Get domain-specific stats

### Search & Analytics
- `POST /search` - Search crawled content
- `GET /page/{url_hash}` - Get specific page details

## Development

### Project Structure
```
crawler/
├── api/                 # API endpoints
├── core/               # Core crawler components
│   ├── frontier/       # URL management
│   ├── fetcher/        # Content fetching
│   ├── parser/         # HTML parsing
│   └── pipeline/       # Data processing
├── ml/                 # Machine learning components
│   ├── content_classifier.py
│   └── url_prioritizer.py
├── storage/            # Storage implementations
├── web/               # Web dashboard
└── monitoring/        # Metrics and monitoring
```

### Adding New Features

1. **New Processors**
   - Create a class inheriting from `PipelineProcessor`
   - Implement the `process` method
   - Add to `DataPipeline.processors`

2. **Custom ML Models**
   - Add model class in `ml/`
   - Implement training and inference methods
   - Update pipeline integration

## Troubleshooting

### Common Issues

1. **Services Not Starting**
   ```bash
   # Check service status
   docker-compose ps
   
   # View logs
   docker-compose logs <service-name>
   ```

2. **Database Connection Issues**
   ```bash
   # Verify PostgreSQL
   psql -h localhost -U crawler -d crawler
   
   # Check Elasticsearch
   curl http://localhost:9200
   ```

3. **Memory Issues**
   - Increase Docker memory limit
   - Adjust JVM heap size for Elasticsearch
   - Monitor with `docker stats`

### Logs

- Application logs: `crawler.log`
- Service logs: `docker-compose logs`
- Access logs: Available in respective service containers

## License

MIT License - See LICENSE file for details