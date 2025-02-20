# Distributed Web Crawler

A high-performance distributed web crawler system capable of crawling billions of pages efficiently, featuring advanced URL prioritization and intelligent content processing.

## Features

### Core Features
- Distributed URL frontier with intelligent prioritization
- High-performance crawler engine with politeness policies
- Robust data extraction and processing pipeline
- Scalable storage system for web data and metadata
- Real-time monitoring and analytics
- Compliance with web standards (robots.txt, rate limits)

### Advanced URL Prioritization
- Multi-factor scoring system
  * Base scoring with domain reputation
  * Freshness-based prioritization
  * Content relevance scoring
  * Domain popularity metrics
- Adaptive scoring based on crawl results
- Pattern-based URL evaluation
- Intelligent domain management

### Data Processing Pipeline
- Content cleaning and normalization
- Advanced keyword extraction and scoring
- Link analysis and relationship scoring
- Content classification and quality assessment
- Modular pipeline architecture
- Real-time content analysis

### Storage and Analytics
- Elasticsearch for full-text search and analytics
- Redis for URL frontier and metadata
- Kafka for distributed message processing
- Prometheus metrics integration
- Comprehensive domain statistics

## Architecture

The system consists of several key components:

1. **URL Frontier**: 
   - Manages URL queue with intelligent prioritization
   - Implements politeness and rate limiting
   - Handles URL deduplication and scoring

2. **Crawler Engine**: 
   - Fetches web pages respecting politeness policies
   - Handles retries and error management
   - Supports concurrent crawling

3. **Parser & Extractor**: 
   - Processes HTML content
   - Extracts metadata and links
   - Performs content analysis

4. **Data Pipeline**:
   - Cleans and normalizes content
   - Extracts and scores keywords
   - Analyzes link relationships
   - Classifies content type and quality

5. **Analytics Engine**: 
   - Processes crawl statistics
   - Generates domain insights
   - Monitors system performance

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start required services:
```bash
# Start Elasticsearch
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" elasticsearch:8.11.1

# Start Redis
docker run -d --name redis -p 6379:6379 redis

# Start Kafka (using docker-compose)
docker-compose up -d
```

5. Start the crawler:
```bash
python -m crawler.main --seed-urls seed_urls.json --num-workers 5
```

## Configuration

The system can be configured through:
- Environment variables
- Configuration files in `config/`
- Command-line arguments

### Key Configuration Options
- `MAX_CONCURRENT_REQUESTS`: Maximum concurrent crawl requests
- `POLITENESS_DELAY`: Delay between requests to same domain
- `URL_BATCH_SIZE`: Number of URLs to process in each batch
- `FRONTIER_WORKER_COUNT`: Number of crawler workers

## Development

### Project Structure
```
crawler/
├── config/           # Configuration files
├── core/             # Core crawler components
│   ├── frontier/     # URL Frontier implementation
│   │   ├── prioritizer.py    # URL scoring system
│   │   └── url_frontier.py   # URL management
│   ├── fetcher/      # Crawler engine
│   ├── parser/       # HTML parsing and extraction
│   └── pipeline/     # Data processing pipeline
├── storage/          # Storage implementations
├── monitoring/       # Monitoring and metrics
├── api/             # API endpoints
└── utils/           # Utility functions
```

### Adding New Features

#### Adding Pipeline Processors
1. Create a new class inheriting from `PipelineProcessor`
2. Implement the `process` method
3. Add the processor to `DataPipeline.processors`

#### Customizing URL Prioritization
1. Modify scoring weights in `URLPrioritizer`
2. Add new scoring factors in `calculate_score`
3. Update domain scoring logic as needed

### Running Tests
```bash
pytest
```

### Monitoring
- Prometheus metrics available at http://localhost:9090/metrics
- API endpoints for statistics at http://localhost:8000/stats
- Domain-specific metrics at http://localhost:8000/domain/{domain}/stats

## License

MIT License - See LICENSE file for details 


pip install -r requirements.txt

python -m spacy download en_core_web_sm
python -m nltk.downloader punkt

curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{
  "query": "positive sentiment",
  "filter": {"sentiment_analysis.overall_sentiment": {"gt": 0.7}}
}'

curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{
  "query": "organization",
  "filter": {"extracted_entities.ORG": "Google"}
}'


curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{
  "query": "technology",
  "filter": {"topic_classification.primary_topic": "technology"}
}'