from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class CrawlerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=True, extra='allow')
    
    # Grafana settings
    GF_SECURITY_ADMIN_USER: str = os.getenv("GF_SECURITY_ADMIN_USER", "admin")
    GF_SECURITY_ADMIN_PASSWORD: str = os.getenv("GF_SECURITY_ADMIN_PASSWORD", "admin")
    GF_USERS_ALLOW_SIGN_UP: bool = os.getenv("GF_USERS_ALLOW_SIGN_UP", "false").lower() == "true"
    
    # Crawler timing settings
    CRAWL_DELAY: float = float(os.getenv("CRAWL_DELAY", "1.0"))
    POLITENESS_DELAY: float = float(os.getenv("POLITENESS_DELAY", "1.0"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6378"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_NEW_URLS: str = "new_urls"
    KAFKA_TOPIC_PROCESSING: str = "processing_urls"
    KAFKA_TOPIC_COMPLETED: str = "completed_urls"
    KAFKA_TOPIC_FAILED: str = "failed_urls"
    
    # Crawler settings
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    
    # Storage settings
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    ELASTICSEARCH_PORT: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    ELASTICSEARCH_USERNAME: str = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
    ELASTICSEARCH_PASSWORD: str = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    
    # PostgreSQL settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5433"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "crawler")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "crawler")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "crawler")
    POSTGRES_POOL_SIZE: int = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
    POSTGRES_MAX_OVERFLOW: int = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
    
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

settings = CrawlerSettings() 