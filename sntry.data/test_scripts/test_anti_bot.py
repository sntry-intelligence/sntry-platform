#!/usr/bin/env python3
"""
Test script for anti-bot countermeasures and rate limiting
"""
import asyncio
import logging
import time
from app.business_directory.scraping.scraping_service import ScrapingService
from app.business_directory.scraping.anti_bot import (
    AntiBot, RateLimitConfig, ProxyConfig, create_default_anti_bot
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_rate_limiting():
    """Test rate limiting functionality"""
    logger.info("Testing rate limiting...")
    
    # Create a strict rate limiter for testing
    rate_config = RateLimitConfig(
        requests_per_minute=5,  # Very low for testing
        min_delay_seconds=1.0,
        max_delay_seconds=2.0,
        burst_limit=2
    )
    
    anti_bot = AntiBot(rate_limit_config=rate_config)
    
    # Test multiple requests to the same domain
    test_url = "https://www.findyello.com"
    
    start_time = time.time()
    for i in range(8):  # More than the per-minute limit
        logger.info(f"Request {i+1}")
        delay = await anti_bot.rate_limiter.wait_if_needed(test_url)
        logger.info(f"Waited {delay:.2f} seconds")
        
        # Simulate request
        anti_bot.rate_limiter.record_request(test_url, True, 0.5)
    
    total_time = time.time() - start_time
    logger.info(f"Total time for 8 requests: {total_time:.2f} seconds")
    
    # Show stats
    stats = anti_bot.rate_limiter.get_stats("www.findyello.com")
    logger.info(f"Rate limiter stats: {stats}")

async def test_human_behavior_simulation():
    """Test human behavior simulation"""
    logger.info("Testing human behavior simulation...")
    
    async with ScrapingService(headless=False) as service:  # Visible for demo
        anti_bot = create_default_anti_bot()
        
        # Create context with anti-bot measures
        context = await anti_bot.create_context(service.browser)
        page = await context.new_page()
        
        try:
            # Navigate with anti-bot measures
            success = await anti_bot.safe_navigate(page, "https://www.findyello.com")
            if success:
                logger.info("Successfully navigated with anti-bot measures")
                
                # Simulate human behavior
                if anti_bot.human_simulator:
                    logger.info("Simulating mouse movement...")
                    await anti_bot.human_simulator.simulate_mouse_movement(page)
                    
                    logger.info("Simulating scrolling...")
                    await anti_bot.human_simulator.simulate_scrolling(page, 3)
                    
                    # Try to interact with search field
                    search_selector = "#home-what"
                    try:
                        await page.wait_for_selector(search_selector, timeout=5000)
                        logger.info("Simulating typing...")
                        await anti_bot.safe_type(page, search_selector, "restaurant")
                        
                        # Wait a bit to see the result
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        logger.warning(f"Could not interact with search field: {e}")
                
                logger.info("Human behavior simulation completed")
            else:
                logger.error("Failed to navigate with anti-bot measures")
                
        finally:
            await context.close()

async def test_user_agent_rotation():
    """Test user agent rotation"""
    logger.info("Testing user agent rotation...")
    
    anti_bot = create_default_anti_bot()
    
    # Test user agent rotation
    user_agents = []
    for i in range(10):
        ua = anti_bot.get_next_user_agent()
        user_agents.append(ua)
        logger.info(f"User agent {i+1}: {ua[:50]}...")
    
    # Check that we got different user agents
    unique_uas = set(user_agents)
    logger.info(f"Got {len(unique_uas)} unique user agents out of {len(user_agents)} requests")

async def test_integrated_scraping_with_anti_bot():
    """Test integrated scraping with anti-bot measures"""
    logger.info("Testing integrated scraping with anti-bot measures...")
    
    # Create anti-bot with moderate settings
    rate_config = RateLimitConfig(
        requests_per_minute=10,
        min_delay_seconds=2.0,
        max_delay_seconds=5.0
    )
    
    anti_bot = AntiBot(rate_limit_config=rate_config)
    
    async with ScrapingService(headless=True) as service:
        # Test scraping with anti-bot measures
        try:
            # Get a scraper and inject anti-bot
            async with service.get_scraper("findyello") as scraper:
                scraper.anti_bot = anti_bot  # Inject our anti-bot system
                
                # Test scraping a small sample
                businesses = await scraper.scrape_category("restaurant", "kingston")
                logger.info(f"Successfully scraped {len(businesses)} businesses with anti-bot measures")
                
                # Show anti-bot stats
                stats = anti_bot.get_stats()
                logger.info(f"Anti-bot stats: {stats}")
                
        except Exception as e:
            logger.error(f"Error in integrated scraping test: {e}")

async def test_proxy_rotation():
    """Test proxy rotation (requires proxy configuration)"""
    logger.info("Testing proxy rotation...")
    
    # Example proxy configuration (these are dummy values)
    proxies = [
        ProxyConfig(host="proxy1.example.com", port=8080),
        ProxyConfig(host="proxy2.example.com", port=8080),
        ProxyConfig(host="proxy3.example.com", port=8080, username="user", password="pass")
    ]
    
    anti_bot = AntiBot(proxies=proxies)
    
    # Test proxy rotation
    for i in range(5):
        proxy = anti_bot.proxy_rotator.get_next_proxy()
        if proxy:
            logger.info(f"Proxy {i+1}: {proxy.host}:{proxy.port}")
            
            # Simulate proxy result
            success = i % 2 == 0  # Alternate success/failure
            anti_bot.proxy_rotator.report_proxy_result(proxy, success)
        else:
            logger.info(f"No proxy available for request {i+1}")
    
    # Show proxy stats
    proxy_stats = anti_bot.proxy_rotator.get_proxy_stats()
    logger.info(f"Proxy stats: {proxy_stats}")

async def main():
    """Run all anti-bot tests"""
    logger.info("Starting anti-bot system tests...")
    
    try:
        await test_rate_limiting()
        await asyncio.sleep(2)
        
        await test_user_agent_rotation()
        await asyncio.sleep(2)
        
        await test_proxy_rotation()
        await asyncio.sleep(2)
        
        # Uncomment to test with actual browser (slower)
        # await test_human_behavior_simulation()
        # await test_integrated_scraping_with_anti_bot()
        
        logger.info("All anti-bot tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in anti-bot tests: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())