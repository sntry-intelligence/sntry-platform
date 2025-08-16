"""
Unified scraping service for Jamaica business directories
Manages Playwright browser instances and coordinates multiple scrapers
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Browser, BrowserContext

from app.business_directory.schemas import BusinessData
from app.business_directory.scraping.base import BaseScraper, ScrapingResult
from app.business_directory.scraping.findyello_scraper import FindYelloScraper
from app.business_directory.scraping.workandjam_scraper import WorkAndJamScraper

logger = logging.getLogger(__name__)


class ScrapingService:
    """
    Unified scraping service that manages multiple scrapers and browser instances
    Provides a single interface for scraping Jamaica business directories
    """
    
    def __init__(self, headless: bool = True, browser_type: str = "chromium"):
        self.headless = headless
        self.browser_type = browser_type
        self.browser: Optional[Browser] = None
        self.playwright = None
        self._scrapers: Dict[str, BaseScraper] = {}
        
    async def __aenter__(self):
        """Async context manager entry - initialize browser"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup browser"""
        await self.stop()
    
    async def start(self):
        """Initialize Playwright and browser"""
        try:
            self.playwright = await async_playwright().start()
            
            # Configure browser launch options
            launch_options = {
                "headless": self.headless,
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding"
                ]
            }
            
            # Launch browser based on type
            if self.browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(**launch_options)
            elif self.browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**launch_options)
            elif self.browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**launch_options)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")
            
            logger.info(f"Browser {self.browser_type} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def stop(self):
        """Cleanup browser and Playwright"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            logger.info("Browser and Playwright stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
    
    @asynccontextmanager
    async def get_scraper(self, website: str) -> BaseScraper:
        """Get a scraper instance for the specified website"""
        if not self.browser:
            raise RuntimeError("Browser not initialized. Call start() first or use as context manager.")
        
        scraper_classes = {
            "findyello": FindYelloScraper,
            "workandjam": WorkAndJamScraper
        }
        
        if website not in scraper_classes:
            raise ValueError(f"Unsupported website: {website}. Supported: {list(scraper_classes.keys())}")
        
        scraper_class = scraper_classes[website]
        scraper = scraper_class(self.browser)
        
        try:
            async with scraper:
                yield scraper
        finally:
            # Scraper cleanup is handled by its context manager
            pass
    
    async def scrape_category(
        self, 
        category: str, 
        location: str = "", 
        websites: Optional[List[str]] = None
    ) -> List[BusinessData]:
        """
        Scrape businesses by category and location from specified websites
        
        Args:
            category: Business category to search for
            location: Location to search in (optional)
            websites: List of websites to scrape from. If None, scrapes all supported sites
            
        Returns:
            List of BusinessData objects from all scraped websites
        """
        if websites is None:
            websites = ["findyello", "workandjam"]
        
        all_businesses = []
        scraping_results = {}
        
        for website in websites:
            try:
                logger.info(f"Starting scraping from {website} for category '{category}' in location '{location}'")
                
                async with self.get_scraper(website) as scraper:
                    businesses = await scraper.scrape_category(category, location)
                    all_businesses.extend(businesses)
                    scraping_results[website] = {
                        "success": True,
                        "count": len(businesses),
                        "error": None
                    }
                    
                logger.info(f"Completed scraping from {website}: {len(businesses)} businesses found")
                
                # Add delay between websites to be respectful
                await asyncio.sleep(2)
                
            except Exception as e:
                error_msg = f"Error scraping from {website}: {str(e)}"
                logger.error(error_msg)
                scraping_results[website] = {
                    "success": False,
                    "count": 0,
                    "error": error_msg
                }
        
        # Log summary
        total_businesses = len(all_businesses)
        successful_sites = sum(1 for result in scraping_results.values() if result["success"])
        
        logger.info(f"Scraping completed: {total_businesses} total businesses from {successful_sites}/{len(websites)} sites")
        logger.info(f"Scraping results: {scraping_results}")
        
        return all_businesses
    
    async def scrape_all_categories(
        self, 
        categories: List[str], 
        location: str = "", 
        websites: Optional[List[str]] = None
    ) -> Dict[str, List[BusinessData]]:
        """
        Scrape multiple categories from specified websites
        
        Args:
            categories: List of business categories to search for
            location: Location to search in (optional)
            websites: List of websites to scrape from
            
        Returns:
            Dictionary mapping category names to lists of BusinessData objects
        """
        results = {}
        
        for category in categories:
            try:
                logger.info(f"Scraping category: {category}")
                businesses = await self.scrape_category(category, location, websites)
                results[category] = businesses
                
                # Add delay between categories
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error scraping category {category}: {e}")
                results[category] = []
        
        return results
    
    async def get_available_categories(self, websites: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Get available categories from specified websites
        
        Args:
            websites: List of websites to get categories from
            
        Returns:
            Dictionary mapping website names to lists of available categories
        """
        if websites is None:
            websites = ["findyello", "workandjam"]
        
        categories = {}
        
        for website in websites:
            try:
                async with self.get_scraper(website) as scraper:
                    site_categories = await scraper.get_categories()
                    categories[website] = site_categories
                    
            except Exception as e:
                logger.error(f"Error getting categories from {website}: {e}")
                categories[website] = []
        
        return categories
    
    async def get_available_locations(self, websites: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Get available locations from specified websites
        
        Args:
            websites: List of websites to get locations from
            
        Returns:
            Dictionary mapping website names to lists of available locations
        """
        if websites is None:
            websites = ["findyello", "workandjam"]
        
        locations = {}
        
        for website in websites:
            try:
                async with self.get_scraper(website) as scraper:
                    site_locations = await scraper.get_locations()
                    locations[website] = site_locations
                    
            except Exception as e:
                logger.error(f"Error getting locations from {website}: {e}")
                locations[website] = []
        
        return locations
    
    async def test_scrapers(self) -> Dict[str, Dict[str, Any]]:
        """
        Test all scrapers to ensure they're working correctly
        
        Returns:
            Dictionary with test results for each scraper
        """
        test_results = {}
        test_category = "restaurant"
        test_location = "kingston"
        
        websites = ["findyello", "workandjam"]
        
        for website in websites:
            test_results[website] = {
                "accessible": False,
                "can_search": False,
                "can_extract_data": False,
                "error": None,
                "test_timestamp": datetime.now().isoformat()
            }
            
            try:
                async with self.get_scraper(website) as scraper:
                    # Test basic accessibility
                    await scraper.page.goto(scraper.base_url, wait_until="networkidle")
                    test_results[website]["accessible"] = True
                    
                    # Test search functionality (limited test)
                    try:
                        businesses = await scraper.scrape_category(test_category, test_location)
                        test_results[website]["can_search"] = True
                        
                        if businesses:
                            test_results[website]["can_extract_data"] = True
                            test_results[website]["sample_business"] = {
                                "name": businesses[0].name,
                                "has_address": bool(businesses[0].raw_address),
                                "has_phone": bool(businesses[0].phone_number)
                            }
                        
                    except Exception as search_error:
                        test_results[website]["error"] = f"Search test failed: {str(search_error)}"
                        
            except Exception as e:
                test_results[website]["error"] = str(e)
        
        return test_results


# Convenience functions for easy usage
async def scrape_jamaica_businesses(
    category: str, 
    location: str = "", 
    websites: Optional[List[str]] = None,
    headless: bool = True
) -> List[BusinessData]:
    """
    Convenience function to scrape Jamaica businesses
    
    Args:
        category: Business category to search for
        location: Location to search in
        websites: List of websites to scrape from
        headless: Whether to run browser in headless mode
        
    Returns:
        List of BusinessData objects
    """
    async with ScrapingService(headless=headless) as service:
        return await service.scrape_category(category, location, websites)


async def test_all_scrapers(headless: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to test all scrapers
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary with test results for each scraper
    """
    async with ScrapingService(headless=headless) as service:
        return await service.test_scrapers()