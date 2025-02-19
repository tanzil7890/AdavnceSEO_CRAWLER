from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class CrawlerMetrics:
    def __init__(self):
        # Counters
        self.pages_crawled = Counter(
            'crawler_pages_crawled_total',
            'Total number of pages crawled'
        )
        self.pages_failed = Counter(
            'crawler_pages_failed_total',
            'Total number of pages that failed to crawl',
            ['error_type']
        )
        self.urls_discovered = Counter(
            'crawler_urls_discovered_total',
            'Total number of URLs discovered'
        )
        self.robots_checked = Counter(
            'crawler_robots_checked_total',
            'Total number of robots.txt files checked'
        )
        
        # Gauges
        self.active_crawlers = Gauge(
            'crawler_active_workers',
            'Number of active crawler workers'
        )
        self.frontier_size = Gauge(
            'crawler_frontier_size',
            'Number of URLs in the frontier'
        )
        self.domain_queue_size = Gauge(
            'crawler_domain_queue_size',
            'Number of URLs in queue per domain',
            ['domain']
        )
        
        # Histograms
        self.page_size = Histogram(
            'crawler_page_size_bytes',
            'Size of crawled pages in bytes',
            buckets=(1000, 10000, 100000, 1000000, 10000000)
        )
        self.crawl_time = Histogram(
            'crawler_request_duration_seconds',
            'Time spent crawling pages',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        self.processing_time = Histogram(
            'crawler_processing_duration_seconds',
            'Time spent processing pages',
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        
        # Domain-specific metrics
        self._domain_metrics: Dict[str, Dict] = {}
        
    def start_server(self, port: int = None):
        """Start the Prometheus metrics server."""
        try:
            if port is None:
                from ..config.settings import settings
                port = settings.PROMETHEUS_PORT
                
            start_http_server(port)
            logger.info(f"Started Prometheus metrics server on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            
    def record_crawl_start(self, url: str):
        """Record the start of a crawl operation."""
        domain = urlparse(url).netloc
        self._ensure_domain_metrics(domain)
        self._domain_metrics[domain]['active_requests'].inc()
        
    def record_crawl_complete(self, url: str, size: int, duration: float, success: bool = True):
        """Record the completion of a crawl operation."""
        domain = urlparse(url).netloc
        self._ensure_domain_metrics(domain)
        
        if success:
            self.pages_crawled.inc()
            self.page_size.observe(size)
            self.crawl_time.observe(duration)
            self._domain_metrics[domain]['success'].inc()
        else:
            self.pages_failed.labels(error_type='http_error').inc()
            self._domain_metrics[domain]['failures'].inc()
            
        self._domain_metrics[domain]['active_requests'].dec()
        
    def record_processing_time(self, duration: float):
        """Record the time spent processing a page."""
        self.processing_time.observe(duration)
        
    def record_urls_discovered(self, count: int, domain: str):
        """Record the number of new URLs discovered."""
        self.urls_discovered.inc(count)
        self._ensure_domain_metrics(domain)
        self._domain_metrics[domain]['urls_discovered'].inc(count)
        
    def update_frontier_size(self, size: int):
        """Update the size of the URL frontier."""
        self.frontier_size.set(size)
        
    def update_domain_queue_size(self, domain: str, size: int):
        """Update the queue size for a specific domain."""
        self.domain_queue_size.labels(domain=domain).set(size)
        
    def record_robots_check(self, success: bool = True):
        """Record a robots.txt check."""
        self.robots_checked.inc()
        if not success:
            self.pages_failed.labels(error_type='robots_error').inc()
            
    def update_active_crawlers(self, count: int):
        """Update the number of active crawler workers."""
        self.active_crawlers.set(count)
        
    def _ensure_domain_metrics(self, domain: str):
        """Ensure domain-specific metrics exist."""
        if domain not in self._domain_metrics:
            self._domain_metrics[domain] = {
                'success': Counter(
                    'crawler_domain_success_total',
                    'Successful crawls per domain',
                    ['domain']
                ).labels(domain=domain),
                'failures': Counter(
                    'crawler_domain_failures_total',
                    'Failed crawls per domain',
                    ['domain']
                ).labels(domain=domain),
                'urls_discovered': Counter(
                    'crawler_domain_urls_discovered_total',
                    'URLs discovered per domain',
                    ['domain']
                ).labels(domain=domain),
                'active_requests': Gauge(
                    'crawler_domain_active_requests',
                    'Active requests per domain',
                    ['domain']
                ).labels(domain=domain)
            }
            
# Global metrics instance
metrics = CrawlerMetrics() 