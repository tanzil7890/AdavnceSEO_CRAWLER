import asyncio
import logging
from typing import Optional, Dict, List
import aiohttp
from datetime import datetime
from urllib.parse import urlparse
import json

from ...config.settings import settings
from ..frontier.url_frontier import URLFrontier

logger = logging.getLogger(__name__)

class CrawlerEngine:
    def __init__(self, frontier: URLFrontier):
        self.frontier = frontier
        self.session: Optional[aiohttp.ClientSession] = None
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize the crawler engine."""
        self.session = aiohttp.ClientSession(
            headers=settings.CUSTOM_HEADERS,
            timeout=aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
        )
        
    async def crawl(self):
        """Main crawling loop."""
        try:
            while True:
                # Get next batch of URLs
                urls = await self.frontier.get_next_urls(
                    batch_size=settings.URL_BATCH_SIZE
                )
                
                if not urls:
                    await asyncio.sleep(1)  # Wait if no URLs available
                    continue
                    
                # Create tasks for each URL
                tasks = []
                for url in urls:
                    if len(self.active_tasks) >= settings.MAX_CONCURRENT_REQUESTS:
                        # Wait for some tasks to complete if we're at capacity
                        done, _ = await asyncio.wait(
                            self.active_tasks.values(),
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        for task in done:
                            task_url = next(
                                url for url, t in self.active_tasks.items()
                                if t == task
                            )
                            del self.active_tasks[task_url]
                            
                    task = asyncio.create_task(self._fetch_url(url))
                    self.active_tasks[url] = task
                    tasks.append(task)
                    
                # Wait for all tasks in this batch
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
        except Exception as e:
            logger.error(f"Error in crawl loop: {e}")
            raise
            
    async def _fetch_url(self, url: str, retry_count: int = 0):
        """Fetch a single URL with retry logic."""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    await self._process_response(url, response, content)
                    await self.frontier.mark_url_complete(url, success=True)
                elif response.status in [429, 503]:  # Rate limited or service unavailable
                    if retry_count < settings.MAX_RETRIES:
                        delay = self._calculate_retry_delay(retry_count)
                        await asyncio.sleep(delay)
                        await self._fetch_url(url, retry_count + 1)
                    else:
                        await self.frontier.mark_url_complete(url, success=False)
                else:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                    await self.frontier.mark_url_complete(url, success=False)
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
            if retry_count < settings.MAX_RETRIES:
                await self._fetch_url(url, retry_count + 1)
            else:
                await self.frontier.mark_url_complete(url, success=False)
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            await self.frontier.mark_url_complete(url, success=False)
            
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
        if self.session:
            await self.session.close()
            
        # Cancel any active tasks
        for task in self.active_tasks.values():
            task.cancel()
            
        try:
            await asyncio.gather(*self.active_tasks.values())
        except asyncio.CancelledError:
            pass
            
class CrawlerWorker:
    def __init__(self):
        self.frontier: Optional[URLFrontier] = None
        self.engine: Optional[CrawlerEngine] = None
        
    async def start(self):
        """Start the crawler worker."""
        self.frontier = await URLFrontier.create()
        self.engine = CrawlerEngine(self.frontier)
        await self.engine.initialize()
        
        try:
            await self.engine.crawl()
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources."""
        if self.engine:
            await self.engine.cleanup()
        if self.frontier:
            await self.frontier.cleanup() 