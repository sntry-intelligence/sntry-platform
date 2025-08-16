"""
Base scraper interface and common functionality
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import random
import logging
from playwright.async_api import Browser, BrowserContext, Page

from app.business_directory.schemas import BusinessData
from app.business_directory.scraping.anti_bot import AntiBot, create_default_anti_bot

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for website scrapers"""
    
    def __init__(self, browser: Browser, base_url: str, anti_bot: Optional[AntiBot] = None):
        self.browser = browser
        self.base_url = base_url
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.anti_bot = anti_bot or create_default_anti_bot()
        
    async def __aenter__(self):
        """Async context manager entry with anti-bot measures"""
        # Use anti-bot system to create context
        self.context = await self.anti_bot.create_context(self.browser)
        self.page = await self.context.new_page()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
    
    async def human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add human-like delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def scroll_page(self, page: Page, scroll_count: int = 3):
        """Simulate human-like scrolling"""
        if self.anti_bot.human_simulator:
            await self.anti_bot.human_simulator.simulate_scrolling(page, scroll_count)
        else:
            # Fallback to simple scrolling
            for _ in range(scroll_count):
                await page.evaluate("window.scrollBy(0, window.innerHeight / 3)")
                await self.human_delay(0.5, 1.5)
    
    async def safe_navigate(self, url: str) -> bool:
        """Safely navigate to a URL with anti-bot measures"""
        if not self.page:
            logger.error("Page not initialized")
            return False
        
        return await self.anti_bot.safe_navigate(self.page, url)
    
    async def safe_click(self, page: Page, selector: str, timeout: int = 5000) -> bool:
        """Safely click an element with error handling and anti-bot measures"""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return await self.anti_bot.safe_click(page, selector)
        except Exception as e:
            logger.warning(f"Failed to click selector {selector}: {e}")
            return False
    
    async def safe_fill(self, page: Page, selector: str, text: str, timeout: int = 5000) -> bool:
        """Safely fill an input field with error handling and anti-bot measures"""
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return await self.anti_bot.safe_type(page, selector, text)
        except Exception as e:
            logger.warning(f"Failed to fill selector {selector}: {e}")
            return False
    
    async def extract_text(self, page: Page, selector: str, default: str = "") -> str:
        """Safely extract text from an element"""
        try:
            element = await page.wait_for_selector(selector, timeout=3000)
            if element:
                text = await element.text_content()
                return text.strip() if text else default
        except Exception as e:
            logger.debug(f"Failed to extract text from {selector}: {e}")
        return default
    
    async def extract_attribute(self, page: Page, selector: str, attribute: str, default: str = "") -> str:
        """Safely extract attribute from an element"""
        try:
            element = await page.wait_for_selector(selector, timeout=3000)
            if element:
                attr_value = await element.get_attribute(attribute)
                return attr_value.strip() if attr_value else default
        except Exception as e:
            logger.debug(f"Failed to extract {attribute} from {selector}: {e}")
        return default
    
    @abstractmethod
    async def scrape_category(self, category: str, location: str = "") -> List[BusinessData]:
        """Scrape businesses by category and location"""
        pass
    
    @abstractmethod
    async def scrape_business_details(self, business_url: str) -> Optional[BusinessData]:
        """Scrape detailed information for a specific business"""
        pass
    
    @abstractmethod
    async def get_categories(self) -> List[str]:
        """Get available business categories"""
        pass
    
    @abstractmethod
    async def get_locations(self) -> List[str]:
        """Get available locations"""
        pass


class ScrapingResult:
    """Container for scraping results and metadata"""
    
    def __init__(self):
        self.businesses: List[BusinessData] = []
        self.errors: List[str] = []
        self.total_pages: int = 0
        self.scraped_pages: int = 0
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.source_website: str = ""
    
    def add_business(self, business: BusinessData):
        """Add a business to results"""
        self.businesses.append(business)
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        logger.error(f"Scraping error: {error}")
    
    def finish(self):
        """Mark scraping as finished"""
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> float:
        """Get scraping duration in seconds"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total_attempts = len(self.businesses) + len(self.errors)
        if total_attempts == 0:
            return 0.0
        return len(self.businesses) / total_attempts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting"""
        return {
            "source_website": self.source_website,
            "total_businesses": len(self.businesses),
            "total_errors": len(self.errors),
            "total_pages": self.total_pages,
            "scraped_pages": self.scraped_pages,
            "duration_seconds": self.duration,
            "success_rate": self.success_rate,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None
        }