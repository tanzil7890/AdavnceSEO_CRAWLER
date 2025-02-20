from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
import asyncpg

from ..config.settings import settings
from ..core.parser.html_parser import ParsedPage

logger = logging.getLogger(__name__)

Base = declarative_base()

class WebPage(Base):
    """SQLAlchemy model for web pages."""
    __tablename__ = 'web_pages'

    url = Column(String, primary_key=True)
    url_hash = Column(String, unique=True, index=True)
    domain = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    raw_content = Column(Text)
    processed_content = Column(Text)
    metadata = Column(JSONB)
    headers = Column(JSONB)
    links = Column(JSONB)
    images = Column(JSONB)
    status_code = Column(Integer)
    content_type = Column(String)
    content_length = Column(Integer)
    crawl_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create indexes for common queries
    __table_args__ = (
        Index('idx_domain_created', domain, created_at),
        Index('idx_content_type', content_type),
    )

class PostgresStorage:
    def __init__(self):
        self.engine = create_async_engine(
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}",
            echo=False
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
    async def initialize(self):
        """Initialize database and create tables."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("PostgreSQL tables created successfully")
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL: {e}")
            raise
            
    async def store_page(self, parsed_page: ParsedPage, metadata: Dict[str, Any]) -> bool:
        """Store a parsed page in PostgreSQL."""
        try:
            async with self.async_session() as session:
                # Create new page object
                page = WebPage(
                    url=parsed_page.url,
                    url_hash=metadata.get("url_hash"),
                    domain=metadata.get("domain", ""),
                    title=parsed_page.title,
                    description=parsed_page.description,
                    raw_content=metadata.get("raw_content", ""),
                    processed_content=parsed_page.text_content,
                    metadata=parsed_page.metadata,
                    headers=parsed_page.headers,
                    links={"urls": parsed_page.links},
                    images={"images": parsed_page.images},
                    status_code=metadata.get("status_code", 0),
                    content_type=metadata.get("content_type", ""),
                    content_length=metadata.get("content_length", 0),
                    crawl_time=metadata.get("crawl_time", 0.0)
                )
                
                # Merge in case the URL already exists
                session.merge(page)
                await session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Error storing page {parsed_page.url} in PostgreSQL: {e}")
            return False
            
    async def get_page(self, url_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve a page by its URL hash."""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    text("SELECT * FROM web_pages WHERE url_hash = :url_hash"),
                    {"url_hash": url_hash}
                )
                page = result.fetchone()
                
                if page:
                    return dict(page)
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving page {url_hash} from PostgreSQL: {e}")
            return None
            
    async def get_domain_pages(
        self,
        domain: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all pages for a specific domain."""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT * FROM web_pages 
                        WHERE domain = :domain 
                        ORDER BY created_at DESC 
                        LIMIT :limit OFFSET :offset
                    """),
                    {
                        "domain": domain,
                        "limit": limit,
                        "offset": offset
                    }
                )
                pages = result.fetchall()
                return [dict(page) for page in pages]
                
        except Exception as e:
            logger.error(f"Error retrieving pages for domain {domain}: {e}")
            return []
            
    async def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get statistics for a specific domain."""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_pages,
                            AVG(content_length) as avg_content_length,
                            AVG(crawl_time) as avg_crawl_time,
                            COUNT(DISTINCT content_type) as content_type_count,
                            MAX(created_at) as last_crawled
                        FROM web_pages 
                        WHERE domain = :domain
                    """),
                    {"domain": domain}
                )
                stats = result.fetchone()
                return dict(stats) if stats else {}
                
        except Exception as e:
            logger.error(f"Error retrieving stats for domain {domain}: {e}")
            return {}
            
    async def cleanup_old_pages(self, days: int = 30) -> int:
        """Remove pages older than specified days."""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    text("""
                        DELETE FROM web_pages 
                        WHERE created_at < NOW() - INTERVAL ':days days'
                        RETURNING 1
                    """),
                    {"days": days}
                )
                deleted_count = len(result.fetchall())
                await session.commit()
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old pages: {e}")
            return 0
            
    async def cleanup(self):
        """Cleanup resources."""
        await self.engine.dispose()
        
    async def create_backup(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            # Use pg_dump through asyncpg
            conn = await asyncpg.connect(
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT
            )
            
            # Create backup
            await conn.execute(f"COPY web_pages TO '{backup_path}' CSV HEADER")
            await conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False 