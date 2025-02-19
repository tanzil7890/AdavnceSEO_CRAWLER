from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import logging
import re
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ParsedPage:
    """Data class to hold parsed page information."""
    url: str
    title: str
    description: str
    keywords: List[str]
    text_content: str
    links: List[str]
    images: List[Dict[str, str]]
    metadata: Dict[str, str]
    headers: Dict[str, List[str]]
    timestamp: str

class HTMLParser:
    def __init__(self):
        self.ignored_extensions = {
            '.pdf', '.doc', '.docx', '.ppt', '.pptx',
            '.xls', '.xlsx', '.zip', '.rar', '.tar',
            '.gz', '.exe', '.dmg', '.iso', '.img',
            '.jpg', '.jpeg', '.png', '.gif', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv'
        }
        
    def parse(self, url: str, html_content: str, headers: Dict[str, str]) -> ParsedPage:
        """Parse HTML content and extract relevant information."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Extract basic metadata
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            keywords = self._extract_keywords(soup)
            
            # Extract text content
            text_content = self._extract_text_content(soup)
            
            # Extract links
            links = self._extract_links(soup, url)
            
            # Extract images
            images = self._extract_images(soup, url)
            
            # Extract metadata
            metadata = self._extract_metadata(soup)
            
            # Extract headers
            headers_dict = self._extract_headers(soup)
            
            return ParsedPage(
                url=url,
                title=title,
                description=description,
                keywords=keywords,
                text_content=text_content,
                links=links,
                images=images,
                metadata=metadata,
                headers=headers_dict,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            raise
            
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
            
        return ""
        
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract page description."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
            
        # Fallback to first paragraph
        first_p = soup.find('p')
        if first_p:
            return first_p.get_text(strip=True)[:200]
            
        return ""
        
    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract keywords from meta tags and content."""
        keywords = set()
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            content = meta_keywords.get('content', '')
            keywords.update(k.strip().lower() for k in content.split(','))
            
        # Extract keywords from headings
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            text = heading.get_text(strip=True).lower()
            words = re.findall(r'\w+', text)
            keywords.update(words)
            
        return list(keywords)
        
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract main text content."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav']):
            element.decompose()
            
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract and normalize links."""
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip anchor links and javascript
            if href.startswith('#') or href.startswith('javascript:'):
                continue
                
            # Normalize URL
            try:
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                
                # Skip unwanted extensions
                if any(parsed.path.lower().endswith(ext) for ext in self.ignored_extensions):
                    continue
                    
                # Only add http(s) URLs
                if parsed.scheme in ('http', 'https'):
                    links.add(absolute_url)
            except Exception as e:
                logger.warning(f"Error processing link {href}: {e}")
                
        return list(links)
        
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image information."""
        images = []
        for img in soup.find_all('img'):
            try:
                src = img.get('src', '')
                if src:
                    image_info = {
                        'url': urljoin(base_url, src),
                        'alt': img.get('alt', ''),
                        'title': img.get('title', ''),
                        'width': img.get('width', ''),
                        'height': img.get('height', '')
                    }
                    images.append(image_info)
            except Exception as e:
                logger.warning(f"Error processing image {src}: {e}")
                
        return images
        
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from meta tags."""
        metadata = {}
        
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            
            if name and content:
                metadata[name.lower()] = content
                
        return metadata
        
    def _extract_headers(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract headers (h1-h6) and their content."""
        headers = {}
        
        for level in range(1, 7):
            tag = f'h{level}'
            headers[tag] = []
            for header in soup.find_all(tag):
                text = header.get_text(strip=True)
                if text:
                    headers[tag].append(text)
                    
        return headers 