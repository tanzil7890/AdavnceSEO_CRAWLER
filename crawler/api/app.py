from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, HttpUrl
import logging
import asyncio
from datetime import datetime

from ..storage.elasticsearch_storage import ElasticsearchStorage
from ..core.frontier.url_frontier import URLFrontier
from ..monitoring.metrics import metrics

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Web Crawler Management API",
    description="API for managing and monitoring the distributed web crawler",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
storage = ElasticsearchStorage()
frontier = None

class CrawlRequest(BaseModel):
    urls: List[HttpUrl]
    priority: Optional[int] = 1
    
class SearchRequest(BaseModel):
    query: str
    size: Optional[int] = 10
    
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global frontier
    try:
        await storage.initialize()
        frontier = await URLFrontier.create()
        metrics.start_server()
    except Exception as e:
        logger.error(f"Failed to initialize API components: {e}")
        raise
        
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if frontier:
        await frontier.cleanup()
    await storage.cleanup()
    
@app.post("/crawl", response_model=Dict[str, Any])
async def add_urls_to_crawl(request: CrawlRequest):
    """Add URLs to the crawler frontier."""
    try:
        results = []
        for url in request.urls:
            success = await frontier.add_url(str(url), request.priority)
            results.append({"url": url, "queued": success})
            
        return {
            "status": "success",
            "queued_urls": len([r for r in results if r["queued"]]),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error adding URLs to frontier: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/stats", response_model=Dict[str, Any])
async def get_crawler_stats():
    """Get current crawler statistics."""
    try:
        return {
            "pages_crawled": metrics.pages_crawled._value.get(),
            "pages_failed": metrics.pages_failed._value.get(),
            "urls_discovered": metrics.urls_discovered._value.get(),
            "active_crawlers": metrics.active_crawlers._value.get(),
            "frontier_size": metrics.frontier_size._value.get(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting crawler stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/domain/{domain}/stats", response_model=Dict[str, Any])
async def get_domain_stats(domain: str):
    """Get statistics for a specific domain."""
    try:
        stats = await storage.get_domain_stats(domain)
        return {
            "domain": domain,
            "stats": stats,
            "queue_size": metrics.domain_queue_size.labels(domain=domain)._value.get()
        }
    except Exception as e:
        logger.error(f"Error getting domain stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/search", response_model=List[Dict[str, Any]])
async def search_pages(request: SearchRequest):
    """Search crawled pages."""
    try:
        results = await storage.search_pages(request.query, request.size)
        return results
    except Exception as e:
        logger.error(f"Error searching pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/page/{url_hash}", response_model=Dict[str, Any])
async def get_page(url_hash: str):
    """Get details of a specific crawled page."""
    try:
        page = await storage.get_page(url_hash)
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        return page
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page {url_hash}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get current Prometheus metrics."""
    try:
        return {
            "crawl_times": {
                "count": metrics.crawl_time._sum.get(),
                "sum": metrics.crawl_time._count.get(),
                "buckets": metrics.crawl_time._buckets
            },
            "processing_times": {
                "count": metrics.processing_time._sum.get(),
                "sum": metrics.processing_time._count.get(),
                "buckets": metrics.processing_time._buckets
            },
            "page_sizes": {
                "count": metrics.page_size._sum.get(),
                "sum": metrics.page_size._count.get(),
                "buckets": metrics.page_size._buckets
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 