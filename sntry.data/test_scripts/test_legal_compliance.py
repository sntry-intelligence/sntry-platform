#!/usr/bin/env python3
"""
Test script for legal compliance and respectful scraping practices
"""
import asyncio
import logging
from app.business_directory.scraping.legal_compliance import (
    LegalComplianceChecker,
    RobotsChecker,
    EthicalScrapingGuidelines,
    check_urls_compliance,
    is_url_allowed,
    get_ethical_guidelines,
    create_scraping_policy
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_robots_txt_checking():
    """Test robots.txt compliance checking"""
    logger.info("Testing robots.txt compliance checking...")
    
    robots_checker = RobotsChecker()
    
    # Test URLs with different robots.txt policies
    test_urls = [
        "https://www.findyello.com/",
        "https://www.findyello.com/jamaica/restaurants/",
        "https://www.google.com/search",  # Should be blocked
        "https://www.example.com/",
        "https://httpbin.org/robots.txt"
    ]
    
    for url in test_urls:
        try:
            allowed = await robots_checker.can_fetch(url)
            crawl_delay = await robots_checker.get_crawl_delay(url)
            
            logger.info(f"URL: {url}")
            logger.info(f"  Allowed: {allowed}")
            logger.info(f"  Crawl delay: {crawl_delay}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"Error checking {url}: {e}")

async def test_compliance_checker():
    """Test comprehensive compliance checking"""
    logger.info("Testing comprehensive compliance checking...")
    
    checker = LegalComplianceChecker()
    
    # Test individual URL compliance
    test_urls = [
        "https://www.findyello.com/jamaica/restaurants/",
        "https://www.findyello.com/admin/",  # Should be flagged as restricted
        "https://www.instagram.com/jamaicatourismboard/",  # Social media
        "https://www.workandjam.com/business-directory/"
    ]
    
    for url in test_urls:
        try:
            compliance = await checker.check_url_compliance(url)
            logger.info(f"URL: {url}")
            logger.info(f"  Compliant: {compliance['compliant']}")
            logger.info(f"  Risk level: {compliance['risk_level']}")
            if compliance['issues']:
                logger.info(f"  Issues: {compliance['issues']}")
            if compliance['recommendations']:
                logger.info(f"  Recommendations: {compliance['recommendations']}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"Error checking compliance for {url}: {e}")

async def test_session_compliance():
    """Test compliance checking for an entire scraping session"""
    logger.info("Testing session compliance checking...")
    
    # Simulate a scraping session with multiple URLs
    session_urls = [
        "https://www.findyello.com/",
        "https://www.findyello.com/jamaica/restaurants/",
        "https://www.findyello.com/jamaica/hotels-resorts/",
        "https://www.findyello.com/jamaica/lawyers/",
        "https://www.workandjam.com/business-directory/",
        "https://www.workandjam.com/jobs/",
        # Add some problematic URLs
        "https://www.findyello.com/admin/",
        "https://www.instagram.com/someaccount/",
    ]
    
    try:
        session_report = await check_urls_compliance(session_urls)
        
        logger.info("Session Compliance Report:")
        logger.info(f"  Total URLs: {session_report['total_urls']}")
        logger.info(f"  Compliant: {session_report['compliant_urls']}")
        logger.info(f"  Non-compliant: {session_report['non_compliant_urls']}")
        logger.info(f"  High-risk: {session_report['high_risk_urls']}")
        logger.info(f"  Overall compliance: {session_report['overall_compliance']}")
        
        if session_report['recommendations']:
            logger.info("  Recommendations:")
            for rec in session_report['recommendations']:
                logger.info(f"    - {rec}")
        
        # Generate and display full report
        checker = LegalComplianceChecker()
        full_report = checker.generate_compliance_report(session_report)
        logger.info("\nFull Compliance Report:")
        logger.info(full_report)
        
    except Exception as e:
        logger.error(f"Error in session compliance test: {e}")

def test_ethical_guidelines():
    """Test ethical guidelines functionality"""
    logger.info("Testing ethical guidelines...")
    
    guidelines = get_ethical_guidelines()
    
    logger.info("Ethical Scraping Guidelines:")
    for category, rules in guidelines.items():
        logger.info(f"\n{category.upper().replace('_', ' ')}:")
        for rule in rules:
            logger.info(f"  • {rule}")

def test_policy_generation():
    """Test scraping policy generation"""
    logger.info("Testing scraping policy generation...")
    
    policy = create_scraping_policy(
        "Jamaica Business Directory Project",
        "contact@jamaicabusiness.com"
    )
    
    logger.info("Generated Scraping Policy:")
    logger.info(policy)

async def test_quick_functions():
    """Test convenience functions"""
    logger.info("Testing convenience functions...")
    
    # Test quick URL checking
    test_url = "https://www.findyello.com/jamaica/restaurants/"
    allowed = await is_url_allowed(test_url)
    logger.info(f"Quick check - {test_url} allowed: {allowed}")
    
    # Test with custom user agent
    allowed_custom = await is_url_allowed(test_url, "MyBot/1.0")
    logger.info(f"Quick check with custom UA - {test_url} allowed: {allowed_custom}")

async def main():
    """Run all legal compliance tests"""
    logger.info("Starting legal compliance tests...")
    
    try:
        await test_robots_txt_checking()
        await asyncio.sleep(1)
        
        await test_compliance_checker()
        await asyncio.sleep(1)
        
        await test_session_compliance()
        await asyncio.sleep(1)
        
        test_ethical_guidelines()
        
        test_policy_generation()
        
        await test_quick_functions()
        
        logger.info("All legal compliance tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in legal compliance tests: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())