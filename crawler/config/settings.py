from pydantic import BaseSettings
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class CrawlerSettings(BaseSettings):
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_NEW_URLS: str = "new_urls"
    KAFKA_TOPIC_PROCESSING: str = "processing_urls"
    KAFKA_TOPIC_COMPLETED: str = "completed_urls"
    KAFKA_TOPIC_FAILED: str = "failed_urls"
    
    # Crawler settings
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    POLITENESS_DELAY: float = float(os.getenv("POLITENESS_DELAY", "1.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # Storage settings
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    
    # Monitoring settings
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # URL Frontier settings
    URL_BATCH_SIZE: int = int(os.getenv("URL_BATCH_SIZE", "1000"))
    FRONTIER_WORKER_COUNT: int = int(os.getenv("FRONTIER_WORKER_COUNT", "5"))
    
    # Domain-specific settings
    ALLOWED_DOMAINS: List[str] = []
    EXCLUDED_DOMAINS: List[str] = []
    CUSTOM_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (compatible; CustomCrawler/1.0; +http://example.com/bot)"
    }
    
    class Config:
        env_file = ".env"

settings = CrawlerSettings() 