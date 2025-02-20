import asyncio
import logging
from typing import Optional, Dict, List
import aiohttp
from datetime import datetime
from urllib.parse import urlparse
import json

from ...config.settings import settings
from ..frontier.url_frontier import URLFrontier
from ...storage.elasticsearch_storage import ElasticsearchStorage
from ..producer.kafka_producer import KafkaProducer
from ...monitoring.metrics import metrics

logger = logging.getLogger(__name__)

class CrawlerEngine:
    def __init__(self, frontier: URLFrontier):
        self.frontier = frontier
        self.session: Optional[aiohttp.ClientSession] = None
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize crawler components."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT),
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MyCrawler/1.0;)",
            }
        )
        
        # Initialize Elasticsearch
        self.storage = ElasticsearchStorage()
        await self.storage.initialize()
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
    async def crawl(self):
        """Main crawling logic."""
        try:
            while True:
                url = await self.frontier.get_next_url()
                if not url:
                    await asyncio.sleep(1)
                    continue
                    
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Store in Elasticsearch
                            await self.storage.store_page({
                                'url': url,
                                'content': content,
                                'title': 'Untitled',  # You might want to parse this from content
                                'timestamp': datetime.utcnow().isoformat(),
                                'status': response.status
                            })
                            
                            # Send to Kafka
                            self.producer.send(
                                settings.KAFKA_TOPIC_COMPLETED,
                                {'url': url, 'status': 'completed'}
                            )
                            
                            logger.info(f"Successfully crawled: {url}")
                        else:
                            logger.warning(f"Failed to fetch {url}: Status {response.status}")
                            
                except Exception as e:
                    logger.error(f"Error crawling {url}: {e}")
                    self.producer.send(
                        settings.KAFKA_TOPIC_FAILED,
                        {'url': url, 'error': str(e)}
                    )
                    
                await asyncio.sleep(settings.POLITENESS_DELAY)
                
        except Exception as e:
            logger.error(f"Crawler engine error: {e}")
            raise
        
    async def _fetch_url(self, url: str):
        try:
            async with self.session.get(url) as response:
                content = await response.text()
                await self.storage.store_page({
                    'url': url,
                    'content': content,
                    'status': response.status,
                    'timestamp': datetime.utcnow().isoformat()
                })
                logger.info(f"Successfully crawled {url}")
                return content
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise
        
    async def _process_response(self, url: str, response: aiohttp.ClientResponse, content: str):
        """Process the fetched content."""
        metadata = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "status_code": response.status,
            "headers": dict(response.headers),
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(content),
        }
        
        # Send to Kafka for processing
        message = {
            "metadata": metadata,
            "content": content
        }
        
        # TODO: Send to processing pipeline
        logger.info(f"Successfully processed {url}")
        
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay."""
        return min(300, (2 ** retry_count) * settings.POLITENESS_DELAY)
        
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                
            if self.producer:
                self.producer.close()
                
            if hasattr(self, 'storage'):
                await self.storage.cleanup()
                
            # Cancel any active tasks
            for task in self.active_tasks.values():
                if not task.done():
                    task.cancel()
                    
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
class CrawlerWorker:
    def __init__(self, worker_id: int, frontier: URLFrontier, storage: ElasticsearchStorage):
        self.worker_id = worker_id
        self.frontier = frontier
        self.storage = storage
        self.session = None
        self.running = True

    async def initialize(self):
        """Initialize the crawler worker."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT),
            headers={
                "User-Agent": f"MyCrawler/{self.worker_id} (compatible;)",
            }
        )
        metrics.active_crawlers.inc()
        logger.info(f"Crawler worker {self.worker_id} initialized")

    async def start(self):
        """Start the crawler worker."""
        logger.info(f"Worker {self.worker_id} starting...")
        try:
            while self.running:
                # Get next URL from frontier
                url = await self.frontier.get_next_url()
                if not url:
                    await asyncio.sleep(1)
                    continue

                try:
                    # Fetch and process the URL
                    async with self.session.get(url) as response:
                        html = await response.text()
                        
                        # Store the page
                        await self.storage.store_page(
                            url=url,
                            html=html,
                            status_code=response.status,
                            content_type=response.headers.get('content-type', ''),
                            metadata={
                                'worker_id': self.worker_id,
                                'crawl_time': datetime.utcnow().isoformat()
                            }
                        )
                        
                        metrics.pages_crawled.inc()
                        
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    continue

                await asyncio.sleep(settings.CRAWL_DELAY)
                
        except asyncio.CancelledError:
            logger.info(f"Worker {self.worker_id} received shutdown signal")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
        metrics.active_crawlers.dec()
        logger.info(f"Crawler worker {self.worker_id} cleaned up") 