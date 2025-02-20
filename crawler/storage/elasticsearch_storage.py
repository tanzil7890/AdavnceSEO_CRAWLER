from elasticsearch import AsyncElasticsearch
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json
from urllib.parse import urlparse

from ..config.settings import settings
from ..core.parser.html_parser import ParsedPage

logger = logging.getLogger(__name__)

class ElasticsearchStorage:
    def __init__(self):
        self.es = AsyncElasticsearch(
            hosts=[f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"],
            basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD),
            verify_certs=False,
            request_timeout=30
        )
        self.index_name = "web_pages"

    async def initialize(self):
        try:
            # Test connection
            await self.es.info()
            
            if not await self.es.indices.exists(index=self.index_name):
                await self.es.indices.create(
                    index=self.index_name,
                    mappings={
                        "properties": {
                            "url": {"type": "keyword"},
                            "content": {"type": "text"},
                            "title": {"type": "text"},
                            "timestamp": {"type": "date"},
                            "status": {"type": "keyword"}
                        }
                    },
                    settings={
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    }
                )
                logger.info(f"Created index {self.index_name}")
        except Exception as e:
            logger.error(f"Elasticsearch initialization error: {e}")
            raise

    async def store_page(self, url: str, html: str, status_code: int, content_type: str, metadata: Optional[Dict] = None):
        """Store a crawled page in Elasticsearch."""
        try:
            if metadata is None:
                metadata = {}
                
            document = {
                "url": url,
                "html": html,
                "status_code": status_code,
                "content_type": content_type,
                "domain": urlparse(url).netloc,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata,
                "content_length": len(html),
                "crawl_time": metadata.get("crawl_time", 0)
            }
            
            await self.es.index(
                index=self.index_name,
                document=document
            )
            
        except Exception as e:
            logger.error(f"Error storing page {url}: {e}")
            raise

    async def get_page(self, url_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve a page by its URL hash."""
        try:
            response = await self.es.get(
                index=self.index_name,
                id=url_hash
            )
            return response["_source"]
        except Exception as e:
            logger.error(f"Error retrieving page {url_hash}: {e}")
            return None
            
    async def search_pages(self, query: str, size: int = 10) -> List[Dict[str, Any]]:
        """Search pages using full-text search."""
        try:
            response = await self.es.search(
                index=self.index_name,
                body={
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "description^2", "text_content"],
                            "type": "best_fields"
                        }
                    },
                    "size": size,
                    "sort": [{"_score": "desc"}]
                }
            )
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
            
        except Exception as e:
            logger.error(f"Error searching pages: {e}")
            return []
            
    async def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get statistics for a specific domain."""
        try:
            response = await self.es.search(
                index=self.index_name,
                body={
                    "query": {"term": {"domain": domain}},
                    "aggs": {
                        "avg_content_length": {"avg": {"field": "content_length"}},
                        "avg_crawl_time": {"avg": {"field": "crawl_time"}},
                        "status_codes": {"terms": {"field": "status_code"}},
                        "content_types": {"terms": {"field": "content_type"}},
                        "crawl_times": {
                            "date_histogram": {
                                "field": "timestamp",
                                "calendar_interval": "day"
                            }
                        }
                    },
                    "size": 0
                }
            )
            
            return response["aggregations"]
            
        except Exception as e:
            logger.error(f"Error getting domain stats for {domain}: {e}")
            return {}
            
    async def cleanup(self):
        if self.es:
            await self.es.close() 