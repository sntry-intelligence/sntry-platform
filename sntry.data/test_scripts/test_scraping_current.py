#!/usr/bin/env python3
"""
Test script to verify current scraping functionality
"""
import asyncio
import logging
from app.business_directory.scraping.scraping_service import ScrapingService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_current_scrapers():
    """Test the current scraping implementation"""
    logger.info("Testing current scraping functionality...")
    
    async with ScrapingService(headless=True) as service:
        # Test scraper accessibility
        test_results = await service.test_scrapers()
        logger.info(f"Scraper test results: {test_results}")
        
        # Test basic scraping with a simple category
        try:
            logger.info("Testing category scraping...")
            businesses = await service.scrape_category("restaurant", "kingston", websites=["findyello"])
            logger.info(f"Found {len(businesses)} businesses from findyello")
            
            if businesses:
                logger.info(f"Sample business: {businesses[0].dict()}")
                
        except Exception as e:
            logger.error(f"Error testing category scraping: {e}")
        
        # Test getting categories
        try:
            logger.info("Testing category retrieval...")
            categories = await service.get_available_categories(websites=["findyello"])
            logger.info(f"Available categories: {categories}")
        except Exception as e:
            logger.error(f"Error getting categories: {e}")

if __name__ == "__main__":
    asyncio.run(test_current_scrapers())