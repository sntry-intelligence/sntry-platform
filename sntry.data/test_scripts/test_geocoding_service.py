#!/usr/bin/env python3
"""
Test script for the geocoding service with caching and cost optimization
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.business_directory.geocoding import GeocodingService, geocoding_service
from app.core.config import settings


async def test_geocoding_service():
    """Test the geocoding service functionality"""
    print("Testing Jamaica Business Directory Geocoding Service")
    print("=" * 60)
    
    # Test addresses (mix of valid and invalid)
    test_addresses = [
        "Half Way Tree, Kingston, Jamaica",
        "Spanish Town, St. Catherine, Jamaica",
        "Montego Bay, St. James, Jamaica",
        "Invalid Address That Should Not Exist",
        "123 Main Street, Kingston 10, Jamaica",
        "University of the West Indies, Mona, Jamaica"
    ]
    
    try:
        # Test 1: Single address geocoding with caching
        print("\n1. Testing single address geocoding with caching:")
        print("-" * 50)
        
        for address in test_addresses[:3]:  # Test first 3 addresses
            print(f"\nGeocoding: {address}")
            
            # First request (should hit API)
            result = await geocoding_service.geocode_address(address)
            print(f"Status: {result.status}")
            if result.status == 'OK':
                print(f"Coordinates: ({result.latitude}, {result.longitude})")
                print(f"Formatted Address: {result.formatted_address}")
                print(f"Place ID: {result.place_id}")
            else:
                print(f"Error: {result.error_message}")
            
            # Second request (should hit cache)
            print("Testing cache hit...")
            cached_result = await geocoding_service.geocode_address(address)
            print(f"Cache result status: {cached_result.status}")
        
        # Test 2: Batch geocoding
        print("\n\n2. Testing batch geocoding:")
        print("-" * 50)
        
        batch_results = await geocoding_service.batch_geocode_with_cache(
            test_addresses, 
            max_concurrent=3
        )
        
        for i, (address, result) in enumerate(zip(test_addresses, batch_results)):
            print(f"\n{i+1}. {address}")
            print(f"   Status: {result.status}")
            if result.status == 'OK':
                print(f"   Coordinates: ({result.latitude}, {result.longitude})")
        
        # Test 3: Cache statistics
        print("\n\n3. Cache Performance Statistics:")
        print("-" * 50)
        cache_stats = geocoding_service.get_cache_stats()
        for key, value in cache_stats.items():
            print(f"{key}: {value}")
        
        # Test 4: Quota and cost status
        print("\n\n4. Quota and Cost Status:")
        print("-" * 50)
        quota_status = geocoding_service.get_quota_status()
        for key, value in quota_status.items():
            if isinstance(value, list):
                print(f"{key}: {', '.join(value) if value else 'None'}")
            else:
                print(f"{key}: {value}")
        
        # Test 5: Cost projection
        print("\n\n5. Cost Projection for 1000 requests:")
        print("-" * 50)
        projection = geocoding_service.get_cost_projection(1000)
        for key, value in projection.items():
            print(f"{key}: {value}")
        
        # Test 6: Comprehensive status
        print("\n\n6. Comprehensive Service Status:")
        print("-" * 50)
        status = await geocoding_service.get_comprehensive_status()
        
        print("Quota and Cost:")
        for key, value in status['quota_and_cost'].items():
            if key != 'alerts':
                print(f"  {key}: {value}")
        
        print("\nCache Performance:")
        for key, value in status['cache_performance'].items():
            print(f"  {key}: {value}")
        
        print("\nOptimization Features:")
        for key, value in status['optimization_features'].items():
            print(f"  {key}: {value}")
        
        if status['quota_and_cost']['alerts']:
            print("\nAlerts:")
            for alert in status['quota_and_cost']['alerts']:
                print(f"  - {alert}")
        
        print("\n" + "=" * 60)
        print("Geocoding service test completed successfully!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


async def test_without_api_key():
    """Test behavior when API key is not configured"""
    print("\n\nTesting without API key:")
    print("-" * 50)
    
    # Temporarily clear the API key
    original_key = settings.GOOGLE_GEOCODING_API_KEY
    settings.GOOGLE_GEOCODING_API_KEY = ""
    
    try:
        service = GeocodingService()
        result = await service.geocode_address("Test Address")
        print(f"Result without API key: {result.status} - {result.error_message}")
    except Exception as e:
        print(f"Expected error without API key: {e}")
    finally:
        # Restore original key
        settings.GOOGLE_GEOCODING_API_KEY = original_key


def main():
    """Main test function"""
    print("Jamaica Business Directory - Geocoding Service Test")
    print("Make sure you have set GOOGLE_GEOCODING_API_KEY in your .env file")
    print()
    
    if not settings.GOOGLE_GEOCODING_API_KEY:
        print("WARNING: GOOGLE_GEOCODING_API_KEY not set in environment variables")
        print("Some tests may fail or return mock results")
        print()
    
    # Run the async tests
    asyncio.run(test_geocoding_service())
    asyncio.run(test_without_api_key())


if __name__ == "__main__":
    main()