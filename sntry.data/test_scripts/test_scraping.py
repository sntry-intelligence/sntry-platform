#!/usr/bin/env python3
"""
Test script for Jamaica business directory scraping
"""
import asyncio
import logging
from app.business_directory.scraping import ScrapingService, test_all_scrapers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Test the scraping functionality"""
    print("Testing Jamaica Business Directory Scrapers")
    print("=" * 50)
    
    # Test scraper accessibility
    print("\n1. Testing scraper accessibility...")
    test_results = await test_all_scrapers(headless=True)
    
    for website, results in test_results.items():
        print(f"\n{website.upper()} Results:")
        print(f"  Accessible: {results['accessible']}")
        print(f"  Can Search: {results['can_search']}")
        print(f"  Can Extract Data: {results['can_extract_data']}")
        if results.get('error'):
            print(f"  Error: {results['error']}")
        if results.get('sample_business'):
            sample = results['sample_business']
            print(f"  Sample Business: {sample['name']}")
            print(f"    Has Address: {sample['has_address']}")
            print(f"    Has Phone: {sample['has_phone']}")
    
    # Test category scraping (limited test)
    print("\n2. Testing category scraping...")
    try:
        async with ScrapingService(headless=True) as service:
            # Test with a small search to avoid overwhelming the sites
            businesses = await service.scrape_category("restaurant", "kingston", ["findyello"])
            print(f"Found {len(businesses)} businesses")
            
            if businesses:
                sample = businesses[0]
                print(f"Sample business: {sample.name}")
                print(f"Address: {sample.raw_address}")
                print(f"Phone: {sample.phone_number}")
                print(f"Source: {sample.source_url}")
    
    except Exception as e:
        print(f"Error during category scraping test: {e}")
    
    print("\nTesting completed!")

if __name__ == "__main__":
    asyncio.run(main())