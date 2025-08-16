#!/usr/bin/env python3
"""
Test script for social media scraping functionality
"""
import asyncio
import logging
from app.business_directory.scraping.scraping_service import ScrapingService
from app.business_directory.scraping.social_media_scraper import (
    SocialMediaScrapingService,
    get_instagram_profile,
    get_tiktok_profile
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_social_media_scrapers():
    """Test the social media scraping functionality"""
    logger.info("Testing social media scraping functionality...")
    
    async with ScrapingService(headless=True) as service:
        # Test Instagram profile scraping (using a known public business account)
        try:
            logger.info("Testing Instagram profile scraping...")
            instagram_profile = await get_instagram_profile(service.browser, "jamaicatourismboard")
            if instagram_profile:
                logger.info(f"Instagram profile found: {instagram_profile.display_name}")
                logger.info(f"Followers: {instagram_profile.follower_count}")
                logger.info(f"Bio: {instagram_profile.bio}")
            else:
                logger.info("No Instagram profile data retrieved")
                
        except Exception as e:
            logger.error(f"Error testing Instagram scraping: {e}")
        
        # Test TikTok profile scraping
        try:
            logger.info("Testing TikTok profile scraping...")
            tiktok_profile = await get_tiktok_profile(service.browser, "jamaicatourismboard")
            if tiktok_profile:
                logger.info(f"TikTok profile found: {tiktok_profile.display_name}")
                logger.info(f"Followers: {tiktok_profile.follower_count}")
                logger.info(f"Bio: {tiktok_profile.bio}")
            else:
                logger.info("No TikTok profile data retrieved")
                
        except Exception as e:
            logger.error(f"Error testing TikTok scraping: {e}")
        
        # Test social media service integration
        try:
            logger.info("Testing social media service integration...")
            social_service = SocialMediaScrapingService(service.browser)
            
            # Test with a sample business name
            profiles = await social_service.get_business_social_profiles("Jamaica Tourism Board")
            logger.info(f"Found social profiles: {list(profiles.keys())}")
            
            for platform, profile in profiles.items():
                logger.info(f"{platform}: @{profile.username} - {profile.follower_count} followers")
                
        except Exception as e:
            logger.error(f"Error testing social media service: {e}")

if __name__ == "__main__":
    asyncio.run(test_social_media_scrapers())