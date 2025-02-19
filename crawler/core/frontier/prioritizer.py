from typing import Dict, List, Optional
import math
from urllib.parse import urlparse
import re
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class URLScore:
    url: str
    base_score: float
    freshness_score: float
    relevance_score: float
    popularity_score: float
    final_score: float

class URLPrioritizer:
    def __init__(self):
        self.domain_scores: Dict[str, float] = {}
        self.url_history: Dict[str, datetime] = {}
        self.keyword_weights: Dict[str, float] = {}
        self.path_patterns: Dict[str, float] = {
            r"/article/": 1.5,
            r"/blog/": 1.3,
            r"/news/": 1.4,
            r"/product/": 1.2,
            r"/category/": 0.8,
            r"/tag/": 0.6,
            r"/page/\d+": 0.5,
        }
        
    def calculate_score(
        self,
        url: str,
        domain_stats: Optional[Dict] = None,
        content_relevance: Optional[float] = None,
        last_crawled: Optional[datetime] = None
    ) -> URLScore:
        """Calculate the priority score for a URL using multiple factors."""
        domain = urlparse(url).netloc
        path = urlparse(url).path
        
        # Base score calculation
        base_score = self._calculate_base_score(domain, path)
        
        # Freshness score
        freshness_score = self._calculate_freshness_score(url, last_crawled)
        
        # Content relevance score
        relevance_score = self._calculate_relevance_score(
            url, content_relevance, domain_stats
        )
        
        # Domain popularity score
        popularity_score = self._calculate_popularity_score(domain, domain_stats)
        
        # Calculate final weighted score
        final_score = (
            base_score * 0.3 +
            freshness_score * 0.2 +
            relevance_score * 0.3 +
            popularity_score * 0.2
        )
        
        return URLScore(
            url=url,
            base_score=base_score,
            freshness_score=freshness_score,
            relevance_score=relevance_score,
            popularity_score=popularity_score,
            final_score=final_score
        )
        
    def _calculate_base_score(self, domain: str, path: str) -> float:
        """Calculate base score using domain reputation and path patterns."""
        score = 1.0
        
        # Apply domain score if available
        domain_score = self.domain_scores.get(domain, 1.0)
        score *= domain_score
        
        # Apply path pattern weights
        for pattern, weight in self.path_patterns.items():
            if re.search(pattern, path):
                score *= weight
                break
                
        # Penalize deep paths
        depth = len([p for p in path.split("/") if p])
        if depth > 3:
            score *= (1.0 / math.log2(depth))
            
        return score
        
    def _calculate_freshness_score(
        self,
        url: str,
        last_crawled: Optional[datetime] = None
    ) -> float:
        """Calculate freshness score based on last crawl time."""
        if not last_crawled:
            return 1.0  # New URLs get maximum freshness
            
        age = datetime.now() - last_crawled
        
        if age < timedelta(hours=1):
            return 0.2  # Recently crawled
        elif age < timedelta(days=1):
            return 0.4
        elif age < timedelta(days=7):
            return 0.6
        elif age < timedelta(days=30):
            return 0.8
        else:
            return 1.0  # Old content needs refresh
            
    def _calculate_relevance_score(
        self,
        url: str,
        content_relevance: Optional[float] = None,
        domain_stats: Optional[Dict] = None
    ) -> float:
        """Calculate relevance score based on content and keywords."""
        score = 1.0
        
        # Use provided content relevance if available
        if content_relevance is not None:
            score *= content_relevance
            
        # Check URL for relevant keywords
        url_lower = url.lower()
        for keyword, weight in self.keyword_weights.items():
            if keyword in url_lower:
                score *= weight
                
        # Consider domain performance
        if domain_stats:
            avg_content_length = domain_stats.get("avg_content_length", 0)
            if avg_content_length > 5000:  # Favor content-rich domains
                score *= 1.2
                
        return score
        
    def _calculate_popularity_score(
        self,
        domain: str,
        domain_stats: Optional[Dict] = None
    ) -> float:
        """Calculate popularity score based on domain statistics."""
        score = 1.0
        
        if domain_stats:
            # Consider successful crawls ratio
            success_count = domain_stats.get("success_count", 0)
            total_count = domain_stats.get("total_count", 1)
            if total_count > 0:
                success_ratio = success_count / total_count
                score *= (0.5 + success_ratio)
                
            # Consider average crawl time
            avg_crawl_time = domain_stats.get("avg_crawl_time", 1.0)
            if avg_crawl_time > 0:
                time_factor = min(1.0, 1.0 / math.log2(1 + avg_crawl_time))
                score *= time_factor
                
        return score
        
    def update_domain_score(self, domain: str, score: float):
        """Update the score for a domain based on crawling results."""
        self.domain_scores[domain] = score
        
    def update_keyword_weight(self, keyword: str, weight: float):
        """Update the weight for a keyword based on its importance."""
        self.keyword_weights[keyword] = weight
        
    def add_path_pattern(self, pattern: str, weight: float):
        """Add a new path pattern with associated weight."""
        self.path_patterns[pattern] = weight 