from typing import Dict, Any, List, Type, Optional
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json
import re
from urllib.parse import urlparse
import hashlib

from ..parser.html_parser import ParsedPage
from ...monitoring.metrics import metrics

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of processing a page through the pipeline."""
    url: str
    success: bool
    processed_data: Dict[str, Any]
    error: Optional[str] = None
    processing_time: float = 0.0

class PipelineProcessor(ABC):
    """Base class for pipeline processors."""
    
    @abstractmethod
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the data and return processed result."""
        pass
        
class ContentCleanerProcessor(PipelineProcessor):
    """Clean and normalize content."""
    
    def __init__(self):
        self.whitespace_pattern = re.compile(r'\s+')
        self.script_pattern = re.compile(r'<script.*?</script>', re.DOTALL)
        self.style_pattern = re.compile(r'<style.*?</style>', re.DOTALL)
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            content = data.get('text_content', '')
            
            # Remove scripts and styles
            content = self.script_pattern.sub('', content)
            content = self.style_pattern.sub('', content)
            
            # Normalize whitespace
            content = self.whitespace_pattern.sub(' ', content)
            
            # Update the data
            data['text_content'] = content.strip()
            data['content_length'] = len(content)
            
            return data
        except Exception as e:
            logger.error(f"Error in content cleaner: {e}")
            raise
            
class KeywordExtractorProcessor(PipelineProcessor):
    """Extract and score keywords from content."""
    
    def __init__(self):
        self.stopwords = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to'])
        self.min_keyword_length = 3
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            content = data.get('text_content', '').lower()
            title = data.get('title', '').lower()
            
            # Extract words and calculate frequencies
            words = re.findall(r'\w+', content)
            word_freq = {}
            
            for word in words:
                if (
                    len(word) >= self.min_keyword_length
                    and word not in self.stopwords
                ):
                    word_freq[word] = word_freq.get(word, 0) + 1
                    
            # Score keywords based on frequency and position
            keyword_scores = {}
            max_freq = max(word_freq.values()) if word_freq else 1
            
            for word, freq in word_freq.items():
                score = freq / max_freq
                
                # Boost score if word appears in title
                if word in title:
                    score *= 1.5
                    
                keyword_scores[word] = score
                
            # Sort and limit keywords
            keywords = sorted(
                keyword_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
            
            data['extracted_keywords'] = [k[0] for k in keywords]
            data['keyword_scores'] = {k: v for k, v in keywords}
            
            return data
        except Exception as e:
            logger.error(f"Error in keyword extractor: {e}")
            raise
            
class LinkAnalyzerProcessor(PipelineProcessor):
    """Analyze and score outbound links."""
    
    def __init__(self):
        self.internal_link_weight = 1.2
        self.external_link_weight = 1.0
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            page_url = data.get('url', '')
            links = data.get('links', [])
            page_domain = urlparse(page_url).netloc
            
            link_analysis = {
                'internal_links': [],
                'external_links': [],
                'link_scores': {}
            }
            
            for link in links:
                link_domain = urlparse(link).netloc
                is_internal = link_domain == page_domain
                
                # Calculate link score
                score = self.internal_link_weight if is_internal else self.external_link_weight
                
                # Adjust score based on link position and context
                if link in data.get('text_content', '')[:1000]:  # Links near the top
                    score *= 1.2
                    
                # Store analysis
                if is_internal:
                    link_analysis['internal_links'].append(link)
                else:
                    link_analysis['external_links'].append(link)
                    
                link_analysis['link_scores'][link] = score
                
            data['link_analysis'] = link_analysis
            
            return data
        except Exception as e:
            logger.error(f"Error in link analyzer: {e}")
            raise
            
class ContentClassifierProcessor(PipelineProcessor):
    """Classify content type and quality."""
    
    def __init__(self):
        self.content_patterns = {
            'article': r'article|post|story|news',
            'product': r'product|price|\$|€|£',
            'landing': r'welcome|homepage|main',
            'listing': r'category|archive|list|index'
        }
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            url = data.get('url', '')
            content = data.get('text_content', '')
            
            # Classify content type
            content_type = 'unknown'
            max_score = 0
            
            for ctype, pattern in self.content_patterns.items():
                score = len(re.findall(pattern, content, re.I))
                if score > max_score:
                    max_score = score
                    content_type = ctype
                    
            # Calculate content quality score
            quality_score = self._calculate_quality_score(data)
            
            data['content_classification'] = {
                'type': content_type,
                'quality_score': quality_score,
                'word_count': len(content.split())
            }
            
            return data
        except Exception as e:
            logger.error(f"Error in content classifier: {e}")
            raise
            
    def _calculate_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate content quality score based on various factors."""
        score = 1.0
        
        # Length factor
        content_length = len(data.get('text_content', ''))
        if content_length > 1000:
            score *= 1.2
        elif content_length < 100:
            score *= 0.8
            
        # Structure factor
        if data.get('headers', {}).get('h1'):
            score *= 1.1
            
        # Metadata completeness
        if data.get('description') and data.get('keywords'):
            score *= 1.1
            
        return min(score, 2.0)  # Cap at 2.0
        
class DataPipeline:
    """Main pipeline coordinator."""
    
    def __init__(self):
        self.processors: List[PipelineProcessor] = [
            ContentCleanerProcessor(),
            KeywordExtractorProcessor(),
            LinkAnalyzerProcessor(),
            ContentClassifierProcessor()
        ]
        
    async def process_page(self, parsed_page: ParsedPage) -> ProcessingResult:
        """Process a parsed page through all pipeline stages."""
        start_time = datetime.now()
        
        try:
            # Convert ParsedPage to dictionary
            data = {
                'url': parsed_page.url,
                'title': parsed_page.title,
                'description': parsed_page.description,
                'keywords': parsed_page.keywords,
                'text_content': parsed_page.text_content,
                'links': parsed_page.links,
                'images': parsed_page.images,
                'metadata': parsed_page.metadata,
                'headers': parsed_page.headers,
                'timestamp': parsed_page.timestamp
            }
            
            # Process through each processor
            for processor in self.processors:
                data = await processor.process(data)
                
            processing_time = (datetime.now() - start_time).total_seconds()
            metrics.record_processing_time(processing_time)
            
            return ProcessingResult(
                url=parsed_page.url,
                success=True,
                processed_data=data,
                processing_time=processing_time
            )
            
        except Exception as e:
            error_msg = f"Pipeline processing failed: {str(e)}"
            logger.error(error_msg)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            metrics.record_processing_time(processing_time)
            
            return ProcessingResult(
                url=parsed_page.url,
                success=False,
                processed_data={},
                error=error_msg,
                processing_time=processing_time
            ) 