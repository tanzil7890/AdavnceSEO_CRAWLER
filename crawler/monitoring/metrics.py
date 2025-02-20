import logging
from prometheus_client import Counter, Gauge, start_http_server
import socket

logger = logging.getLogger(__name__)

class CrawlerMetrics:
    def __init__(self, port: int = 9090):
        self.port = port
        
        # Initialize metrics
        self.pages_crawled = Counter('pages_crawled_total', 'Total number of pages crawled')
        self.pages_failed = Counter('pages_failed_total', 'Total number of failed page crawls', ['error_type'])
        self.urls_discovered = Counter('urls_discovered_total', 'Total number of URLs discovered')
        self.robots_checked = Counter('robots_checked_total', 'Total number of robots.txt files checked')
        self.active_crawlers = Gauge('active_crawlers', 'Number of active crawler workers')
        self.frontier_size = Gauge('frontier_size', 'Current size of URL frontier')

    def start_server(self):
        """Start the Prometheus metrics server."""
        max_retries = 5
        current_port = self.port

        for _ in range(max_retries):
            try:
                start_http_server(current_port)
                logger.info(f"Started metrics server on port {current_port}")
                return
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    current_port += 1
                    logger.warning(f"Port {current_port-1} in use, trying {current_port}")
                else:
                    raise
        
        raise RuntimeError(f"Could not find an available port after {max_retries} attempts")

    def update_frontier_size(self, size: int):
        """Update frontier size metric."""
        self.frontier_size.set(size)

    def record_robots_check(self, success: bool):
        """Record robots.txt check."""
        self.robots_checked.inc()

# Create a global metrics instance
metrics = CrawlerMetrics()