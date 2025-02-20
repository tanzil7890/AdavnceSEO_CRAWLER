from typing import Dict, Any, List, Type, Optional
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json
import re
from urllib.parse import urlparse
import hashlib
import asyncio
from textblob import TextBlob
import spacy
from transformers import pipeline
import nltk
from nltk.tokenize import sent_tokenize
import torch

from ..parser.html_parser import ParsedPage
from ...monitoring.metrics import metrics

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    spacy.cli.download('en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')

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
        
class SentimentAnalysisProcessor(PipelineProcessor):
    """Analyze sentiment of text content."""
    
    def __init__(self):
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=0 if torch.cuda.is_available() else -1
        )
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text_content = data.get('text_content', '')
            
            # Split text into sentences for more granular analysis
            sentences = sent_tokenize(text_content[:5000])  # Limit to first 5000 chars
            
            # Analyze sentiment of each sentence
            sentiments = []
            for sentence in sentences:
                if len(sentence.strip()) > 10:  # Only analyze meaningful sentences
                    result = self.sentiment_analyzer(sentence)[0]
                    sentiments.append({
                        'text': sentence,
                        'label': result['label'],
                        'score': result['score']
                    })
            
            # Calculate overall sentiment
            positive_count = sum(1 for s in sentiments if s['label'] == 'POSITIVE')
            total_count = len(sentiments)
            overall_sentiment = positive_count / total_count if total_count > 0 else 0.5
            
            # Add sentiment analysis results
            data['sentiment_analysis'] = {
                'overall_sentiment': overall_sentiment,
                'sentence_sentiments': sentiments[:10],  # Store top 10 sentences
                'positive_sentences': positive_count,
                'total_sentences': total_count
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            data['sentiment_analysis'] = {
                'error': str(e),
                'overall_sentiment': 0.5
            }
            return data

class EntityExtractionProcessor(PipelineProcessor):
    """Extract named entities from text content."""
    
    def __init__(self):
        self.ner_pipeline = pipeline(
            "ner",
            model="dbmdz/bert-large-cased-finetuned-conll03-english",
            device=0 if torch.cuda.is_available() else -1
        )
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text_content = data.get('text_content', '')
            
            # Use spaCy for initial entity extraction
            doc = nlp(text_content[:10000])  # Limit to first 10000 chars
            
            # Extract entities using spaCy
            spacy_entities = {}
            for ent in doc.ents:
                if ent.label_ not in spacy_entities:
                    spacy_entities[ent.label_] = []
                if ent.text not in spacy_entities[ent.label_]:
                    spacy_entities[ent.label_].append(ent.text)
                    
            # Use transformers for additional entity detection
            transformer_entities = self.ner_pipeline(text_content[:5000])
            
            # Merge and deduplicate entities
            processed_entities = {
                'PERSON': [],
                'ORG': [],
                'LOC': [],
                'MISC': []
            }
            
            # Process spaCy entities
            for label, entities in spacy_entities.items():
                category = self._map_entity_type(label)
                if category:
                    processed_entities[category].extend(entities)
                    
            # Process transformer entities
            for entity in transformer_entities:
                category = self._map_entity_type(entity['entity'])
                if category and entity['word'] not in processed_entities[category]:
                    processed_entities[category].append(entity['word'])
                    
            # Deduplicate and limit entities
            for category in processed_entities:
                processed_entities[category] = list(set(processed_entities[category]))[:10]
                
            data['extracted_entities'] = processed_entities
            
            return data
            
        except Exception as e:
            logger.error(f"Error in entity extraction: {e}")
            data['extracted_entities'] = {
                'error': str(e),
                'entities': {}
            }
            return data
            
    def _map_entity_type(self, entity_type: str) -> Optional[str]:
        """Map different entity type notations to common categories."""
        person_types = {'PERSON', 'PER', 'B-PER', 'I-PER'}
        org_types = {'ORG', 'ORGANIZATION', 'B-ORG', 'I-ORG'}
        loc_types = {'LOC', 'GPE', 'LOCATION', 'B-LOC', 'I-LOC'}
        
        if entity_type in person_types:
            return 'PERSON'
        elif entity_type in org_types:
            return 'ORG'
        elif entity_type in loc_types:
            return 'LOC'
        else:
            return 'MISC'

class TopicClassificationProcessor(PipelineProcessor):
    """Classify content into topics."""
    
    def __init__(self):
        self.classifier = pipeline(
            "text-classification",
            model="facebook/bart-large-mnli",
            device=0 if torch.cuda.is_available() else -1
        )
        self.topics = [
            "technology", "business", "politics", "science",
            "health", "entertainment", "sports", "education"
        ]
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            text_content = data.get('text_content', '')
            title = data.get('title', '')
            
            # Combine title and beginning of content for classification
            classification_text = f"{title}. {text_content[:1000]}"
            
            # Classify content against each topic
            topic_scores = []
            for topic in self.topics:
                result = self.classifier(
                    f"This text is about {topic}: {classification_text}",
                    truncation=True
                )[0]
                topic_scores.append({
                    'topic': topic,
                    'score': result['score'] if result['label'] == 'ENTAILMENT' else 1 - result['score']
                })
                
            # Sort topics by score
            topic_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Get main topics (those with score > 0.5)
            main_topics = [t['topic'] for t in topic_scores if t['score'] > 0.5]
            
            data['topic_classification'] = {
                'main_topics': main_topics[:3],  # Top 3 topics
                'topic_scores': topic_scores,
                'primary_topic': topic_scores[0]['topic'] if topic_scores else None
            }
            
            return data
            
        except Exception as e:
            logger.error(f"Error in topic classification: {e}")
            data['topic_classification'] = {
                'error': str(e),
                'main_topics': [],
                'primary_topic': None
            }
            return data

class DataPipeline:
    """Main pipeline coordinator."""
    
    def __init__(self):
        self.processors: List[PipelineProcessor] = [
            ContentCleanerProcessor(),
            KeywordExtractorProcessor(),
            LinkAnalyzerProcessor(),
            ContentClassifierProcessor(),
            SentimentAnalysisProcessor(),
            EntityExtractionProcessor(),
            TopicClassificationProcessor()
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