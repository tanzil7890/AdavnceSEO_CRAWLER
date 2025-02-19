import asyncio
from typing import List, Set, Dict, Optional
from datetime import datetime, timedelta
import hashlib
import logging
from urllib.parse import urlparse
import aioredis
from kafka import KafkaProducer, KafkaConsumer
from bloom_filter2 import BloomFilter
import robotexclusionrulesparser
import aiohttp

from ...config.settings import settings
from .prioritizer import URLPrioritizer, URLScore
from ...monitoring.metrics import metrics

logger = logging.getLogger(__name__)

class URLFrontier:
    def __init__(self):
        self.redis = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )
        self.bloom_filter = BloomFilter(max_elements=10000000, error_rate=0.001)
        self.domain_access_times: Dict[str, datetime] = {}
        self.robots_parser = robotexclusionrulesparser.RobotExclusionRulesParser()
        self.robots_cache: Dict[str, str] = {}
        self.prioritizer = URLPrioritizer()
        
        # Kafka setup
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda x: str(x).encode('utf-8')
        )
        
    async def add_url(self, url: str, priority: int = 1, domain_stats: Optional[Dict] = None) -> bool:
        """Add a URL to the frontier if it hasn't been seen before."""
        url_hash = self._get_url_hash(url)
        
        if url_hash in self.bloom_filter:
            return False
            
        domain = urlparse(url).netloc
        if not await self._is_allowed_by_robots(url):
            logger.info(f"URL {url} not allowed by robots.txt")
            return False
            
        self.bloom_filter.add(url_hash)
        
        # Calculate URL score using the prioritizer
        score = await self._calculate_url_score(url, priority, domain_stats)
        
        # Store URL with calculated score
        await self.redis.zadd(
            "frontier:urls",
            {url: score.final_score}
        )
        
        # Store additional URL metadata
        await self.redis.hset(
            f"frontier:metadata:{url_hash}",
            mapping={
                "base_score": score.base_score,
                "freshness_score": score.freshness_score,
                "relevance_score": score.relevance_score,
                "popularity_score": score.popularity_score,
                "added_time": datetime.now().isoformat()
            }
        )
        
        # Update domain queue size metric
        domain_queue_size = await self.redis.zcount(
            "frontier:urls",
            float('-inf'),
            float('inf')
        )
        metrics.update_domain_queue_size(domain, domain_queue_size)
        
        # Publish to Kafka for distributed processing
        self.producer.send(
            settings.KAFKA_TOPIC_NEW_URLS,
            value=url
        )
        
        return True
        
    async def get_next_urls(self, batch_size: int = 100) -> List[str]:
        """Get the next batch of URLs to crawl, respecting politeness policies."""
        current_time = datetime.now()
        urls = []
        
        # Get URLs with highest scores
        candidates = await self.redis.zrange(
            "frontier:urls",
            0,
            batch_size - 1,
            withscores=True
        )
        
        for url, score in candidates:
            url = url.decode('utf-8')
            domain = urlparse(url).netloc
            
            # Check domain politeness
            last_access = self.domain_access_times.get(domain)
            if last_access and (current_time - last_access).total_seconds() < settings.POLITENESS_DELAY:
                continue
                
            urls.append(url)
            self.domain_access_times[domain] = current_time
            
            # Remove URL from Redis
            await self.redis.zrem("frontier:urls", url)
            
            # Update metrics
            metrics.update_domain_queue_size(
                domain,
                await self.redis.zcount(
                    "frontier:urls",
                    float('-inf'),
                    float('inf')
                )
            )
            
        return urls
        
    async def _calculate_url_score(
        self,
        url: str,
        base_priority: int,
        domain_stats: Optional[Dict] = None
    ) -> URLScore:
        """Calculate URL score using the prioritizer."""
        # Get last crawl time if available
        url_hash = self._get_url_hash(url)
        metadata = await self.redis.hgetall(f"frontier:metadata:{url_hash}")
        last_crawled = None
        if metadata:
            last_crawled_str = metadata.get(b'last_crawled', None)
            if last_crawled_str:
                last_crawled = datetime.fromisoformat(last_crawled_str.decode('utf-8'))
                
        # Calculate score
        return self.prioritizer.calculate_score(
            url=url,
            domain_stats=domain_stats,
            last_crawled=last_crawled
        )
        
    async def _is_allowed_by_robots(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        domain = urlparse(url).netloc
        if domain not in self.robots_cache:
            try:
                robots_url = f"http://{domain}/robots.txt"
                async with aiohttp.ClientSession() as session:
                    async with session.get(robots_url) as response:
                        if response.status == 200:
                            robots_content = await response.text()
                            self.robots_cache[domain] = robots_content
                            self.robots_parser.parse(robots_content)
                            metrics.record_robots_check(success=True)
                        else:
                            metrics.record_robots_check(success=False)
                            return True
            except Exception as e:
                logger.error(f"Error fetching robots.txt for {domain}: {e}")
                metrics.record_robots_check(success=False)
                return True
                
        return self.robots_parser.is_allowed(
            settings.CUSTOM_HEADERS["User-Agent"],
            urlparse(url).path
        )
        
    def _get_url_hash(self, url: str) -> str:
        """Generate a hash for URL deduplication."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
        
    async def mark_url_complete(self, url: str, success: bool = True, stats: Optional[Dict] = None):
        """Mark a URL as completed or failed and update statistics."""
        url_hash = self._get_url_hash(url)
        domain = urlparse(url).netloc
        
        # Update URL metadata
        metadata = {
            "last_crawled": datetime.now().isoformat(),
            "last_status": "success" if success else "failed"
        }
        
        if stats:
            metadata.update(stats)
            
        await self.redis.hset(
            f"frontier:metadata:{url_hash}",
            mapping=metadata
        )
        
        # Update domain statistics
        if stats:
            # Update domain score based on crawl results
            domain_score = self._calculate_domain_score(stats)
            self.prioritizer.update_domain_score(domain, domain_score)
            
        # Send to appropriate Kafka topic
        topic = settings.KAFKA_TOPIC_COMPLETED if success else settings.KAFKA_TOPIC_FAILED
        self.producer.send(topic, value=url)
        
    def _calculate_domain_score(self, stats: Dict) -> float:
        """Calculate domain score based on crawl statistics."""
        score = 1.0
        
        # Consider content quality
        quality_score = stats.get('quality_score', 0.0)
        score *= (1.0 + quality_score)
        
        # Consider crawl performance
        crawl_time = stats.get('crawl_time', 1.0)
        if crawl_time > 0:
            score *= min(1.0, 1.0 / crawl_time)
            
        # Consider content size
        content_length = stats.get('content_length', 0)
        if content_length > 5000:
            score *= 1.2
            
        return min(score, 2.0)  # Cap at 2.0
        
    async def cleanup(self):
        """Cleanup resources."""
        await self.redis.close()
        self.producer.close()
        
    @classmethod
    async def create(cls) -> 'URLFrontier':
        """Factory method to create and initialize URLFrontier instance."""
        frontier = cls()
        return frontier 