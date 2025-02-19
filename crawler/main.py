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

from .core.frontier.url_frontier import URLFrontier
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
    def __init__(self, seed_urls: List[str], num_workers: int = 5):
        self.seed_urls = seed_urls
        self.num_workers = num_workers
        self.workers: List[CrawlerWorker] = []
        self.running = True
        self.frontier: URLFrontier = None
        self.storage: ElasticsearchStorage = None
        
    async def initialize(self):
        """Initialize the crawler manager and workers."""
        logger.info("Initializing crawler manager...")
        
        # Initialize storage
        self.storage = ElasticsearchStorage()
        await self.storage.initialize()
        
        # Create and initialize URL frontier
        self.frontier = await URLFrontier.create()
        
        # Add seed URLs to frontier
        for url in self.seed_urls:
            await self.frontier.add_url(url, priority=10)  # High priority for seed URLs
            
        # Create workers
        self.workers = [CrawlerWorker() for _ in range(self.num_workers)]
        
        # Setup signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._signal_handler)
            
        # Start metrics server
        metrics.start_server()
        metrics.update_active_crawlers(self.num_workers)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Starting graceful shutdown...")
        self.running = False
        
    async def start(self):
        """Start the crawler workers and API server."""
        logger.info(f"Starting {self.num_workers} crawler workers...")
        
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
                    
                # Update metrics
                metrics.update_frontier_size(len(self.frontier.bloom_filter))
                
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
            
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Distributed Web Crawler")
    parser.add_argument(
        "--seed-urls",
        type=str,
        required=True,
        help="JSON file containing seed URLs"
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=settings.FRONTIER_WORKER_COUNT,
        help="Number of crawler workers"
    )
    return parser.parse_args()
    
async def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        # Load seed URLs
        with open(args.seed_urls) as f:
            seed_urls = json.load(f)
            
        # Create and start crawler manager
        manager = CrawlerManager(
            seed_urls=seed_urls,
            num_workers=args.num_workers
        )
        
        await manager.initialize()
        await manager.start()
        
    except Exception as e:
        logger.error(f"Crawler failed with error: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1) 