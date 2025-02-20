import asyncio
import logging
import sys
import argparse
from typing import List
import signal
from concurrent.futures import ThreadPoolExecutor
import json
import uvicorn
from datetime import datetime

from crawler.core.frontier.url_frontier import URLFrontier
from .core.fetcher.crawler import CrawlerWorker
from .storage.elasticsearch_storage import ElasticsearchStorage
from .monitoring.metrics import metrics
from .api.app import app
from .config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('crawler.log')
    ]
)

logger = logging.getLogger(__name__)

class CrawlerManager:
    def __init__(self, seed_urls: str, num_workers: int = 5):
        """Initialize the crawler manager.
        
        Args:
            seed_urls (str): Path to JSON file containing seed URLs
            num_workers (int): Number of crawler workers to spawn
        """
        self.seed_urls = seed_urls
        self.num_workers = num_workers
        self.running = True
        self.storage = ElasticsearchStorage()
        self.frontier = URLFrontier()
        self.workers = []
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    async def initialize(self):
        """Initialize the crawler manager."""
        try:
            # Start metrics server
            metrics.start_server()
            
            # Initialize storage
            await self.storage.initialize()
            
            # Initialize frontier
            await self.frontier.initialize()
            
            # Initialize workers
            self.workers = [
                CrawlerWorker(
                    worker_id=i,
                    frontier=self.frontier,
                    storage=self.storage
                ) for i in range(self.num_workers)
            ]
            
            # Initialize each worker
            for worker in self.workers:
                await worker.initialize()
                
            logger.info("Crawler manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing crawler: {e}")
            raise
        
    async def initialize_frontier(self):
        """Initialize the URL frontier with seed URLs."""
        try:
            # Read seed URLs from JSON file
            with open(self.seed_urls, 'r') as f:
                seed_urls = json.load(f)
                
            if isinstance(seed_urls, str):
                seed_urls = [seed_urls]
            elif not isinstance(seed_urls, list):
                raise ValueError("Seed URLs must be a string or list of strings")
                
            # Add each URL to the frontier
            for url in seed_urls:
                # Normalize URL
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                    
                added = await self.frontier.add_url(url)
                if added:
                    await self.frontier.redis.rpush('frontier:urls', url)
                    metrics.urls_discovered.inc()
                    
            logger.info(f"Added {len(seed_urls)} seed URLs to frontier")
            
        except Exception as e:
            logger.error(f"Error initializing frontier with seed URLs: {e}")
            raise
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Starting graceful shutdown...")
        self.running = False
        
    async def start(self):
        """Start the crawler workers and API server."""
        logger.info(f"Starting {self.num_workers} crawler workers...")
        
        # Initialize frontier with seed URLs
        await self.initialize_frontier()
        
        # Start API server
        api_config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        api_server = uvicorn.Server(api_config)
        api_task = asyncio.create_task(api_server.serve())
        
        # Create tasks for each worker
        worker_tasks = [
            asyncio.create_task(worker.start())
            for worker in self.workers
        ]
        
        try:
            # Wait for all workers to complete or until shutdown
            while self.running:
                done, pending = await asyncio.wait(
                    worker_tasks,
                    timeout=1,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Handle completed tasks
                for task in done:
                    try:
                        await task
                    except Exception as e:
                        logger.error(f"Worker failed with error: {e}")
                        metrics.pages_failed.labels(error_type='worker_error').inc()
                        
                # Break if all tasks are done
                if not pending:
                    break
                    
                # Update metrics using the new size property
                metrics.update_frontier_size(self.frontier.size)
                
        except asyncio.CancelledError:
            logger.info("Crawler manager received cancellation request")
        finally:
            # Cancel any remaining tasks
            for task in worker_tasks:
                if not task.done():
                    task.cancel()
                    
            # Cancel API server
            api_task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*worker_tasks, return_exceptions=True)
            
            # Cleanup
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up crawler manager resources...")
        
        # Cleanup workers
        cleanup_tasks = [
            worker.cleanup()
            for worker in self.workers
        ]
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        # Cleanup frontier and storage
        if self.frontier:
            await self.frontier.cleanup()
        if self.storage:
            await self.storage.cleanup()
            
async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed-urls', required=True, help='Path to seed URLs file')
    parser.add_argument('--num-workers', type=int, default=5, help='Number of crawler workers')
    args = parser.parse_args()
    
    try:
        # Load seed URLs
        with open(args.seed_urls) as f:
            seed_urls = json.load(f)
            
        # Initialize and start crawler
        manager = CrawlerManager(seed_urls=args.seed_urls, num_workers=args.num_workers)
        await manager.initialize()
        await manager.start()
        
    except Exception as e:
        logger.error(f"Crawler failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 