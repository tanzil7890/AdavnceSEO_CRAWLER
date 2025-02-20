from elasticsearch import AsyncElasticsearch
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from ..config.settings import settings
from ..core.parser.html_parser import ParsedPage

logger = logging.getLogger(__name__)

class ElasticsearchStorage:
    def __init__(self):
        # Properly format the Elasticsearch URL
        elasticsearch_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"
        self.es = AsyncElasticsearch(
            hosts=[elasticsearch_url],
            verify_certs=False,
            request_timeout=30
        )
        self.index_name = "web_pages"
        self.index_settings = {
            "settings": {
                "number_of_shards": 5,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "html_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "char_filter": ["html_strip"],
                            "filter": ["lowercase", "stop", "snowball"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "url": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "html_analyzer"},
                    "description": {"type": "text", "analyzer": "html_analyzer"},
                    "keywords": {"type": "keyword"},
                    "text_content": {"type": "text", "analyzer": "html_analyzer"},
                    "links": {"type": "keyword"},
                    "images": {"type": "nested"},
                    "metadata": {"type": "object"},
                    "headers": {"type": "object"},
                    "timestamp": {"type": "date"},
                    "domain": {"type": "keyword"},
                    "content_type": {"type": "keyword"},
                    "content_length": {"type": "long"},
                    "status_code": {"type": "integer"},
                    "crawl_time": {"type": "float"},
                    "sentiment_analysis": {
                        "type": "object",
                        "properties": {
                            "overall_sentiment": {"type": "float"},
                            "sentence_sentiments": {
                                "type": "nested",
                                "properties": {
                                    "text": {"type": "text"},
                                    "label": {"type": "keyword"},
                                    "score": {"type": "float"}
                                }
                            },
                            "positive_sentences": {"type": "integer"},
                            "total_sentences": {"type": "integer"}
                        }
                    },
                    "extracted_entities": {
                        "type": "object",
                        "properties": {
                            "PERSON": {"type": "keyword"},
                            "ORG": {"type": "keyword"},
                            "LOC": {"type": "keyword"},
                            "MISC": {"type": "keyword"}
                        }
                    },
                    "topic_classification": {
                        "type": "object",
                        "properties": {
                            "main_topics": {"type": "keyword"},
                            "primary_topic": {"type": "keyword"},
                            "topic_scores": {
                                "type": "nested",
                                "properties": {
                                    "topic": {"type": "keyword"},
                                    "score": {"type": "float"}
                                }
                            }
                        }
                    }
                }
            }
        }
        
    async def initialize(self):
        """Initialize Elasticsearch indices and mappings."""
        try:
            if not await self.es.indices.exists(index=self.index_name):
                await self.es.indices.create(
                    index=self.index_name,
                    body=self.index_settings
                )
                logger.info(f"Created index {self.index_name}")
        except Exception as e:
            logger.error(f"Error initializing Elasticsearch: {e}")
            raise
            
    async def store_page(self, parsed_page: ParsedPage, metadata: Dict[str, Any]) -> bool:
        """Store a parsed page in Elasticsearch."""
        try:
            document = {
                "url": parsed_page.url,
                "title": parsed_page.title,
                "description": parsed_page.description,
                "keywords": parsed_page.keywords,
                "text_content": parsed_page.text_content,
                "links": parsed_page.links,
                "images": parsed_page.images,
                "metadata": parsed_page.metadata,
                "headers": parsed_page.headers,
                "timestamp": parsed_page.timestamp,
                "domain": metadata.get("domain", ""),
                "content_type": metadata.get("content_type", ""),
                "content_length": metadata.get("content_length", 0),
                "status_code": metadata.get("status_code", 0),
                "crawl_time": metadata.get("crawl_time", 0.0),
                "sentiment_analysis": {
                    "overall_sentiment": metadata.get("sentiment_analysis", {}).get("overall_sentiment", 0.0),
                    "sentence_sentiments": metadata.get("sentiment_analysis", {}).get("sentence_sentiments", []),
                    "positive_sentences": metadata.get("sentiment_analysis", {}).get("positive_sentences", 0),
                    "total_sentences": metadata.get("sentiment_analysis", {}).get("total_sentences", 0)
                },
                "extracted_entities": metadata.get("extracted_entities", {}),
                "topic_classification": metadata.get("topic_classification", {})
            }
            
            response = await self.es.index(
                index=self.index_name,
                body=document,
                id=metadata.get("url_hash")
            )
            
            return response["result"] in ("created", "updated")
            
        except Exception as e:
            logger.error(f"Error storing page {parsed_page.url}: {e}")
            return False
            
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
        """Cleanup resources."""
        await self.es.close() 