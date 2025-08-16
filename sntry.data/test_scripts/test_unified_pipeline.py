#!/usr/bin/env python3
"""
Test script for the unified data pipeline
"""
import asyncio
import logging
from app.business_directory.scraping.unified_pipeline import (
    UnifiedDataPipeline,
    scrape_businesses_with_insights,
    generate_lead_report
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_unified_pipeline():
    """Test the unified data pipeline functionality"""
    logger.info("Testing unified data pipeline...")
    
    try:
        # Test basic pipeline functionality
        logger.info("Testing basic pipeline with restaurant category...")
        
        async with UnifiedDataPipeline(headless=True) as pipeline:
            # Test with a small sample
            customer_360_data = await pipeline.scrape_businesses_with_customer_360(
                category="restaurant",
                location="kingston",
                include_social_media=False,  # Disable for faster testing
                include_sentiment=True,
                websites=["findyello"]  # Just test with FindYello for speed
            )
            
            logger.info(f"Retrieved {len(customer_360_data)} businesses with customer 360 data")
            
            if customer_360_data:
                # Show sample data
                sample = customer_360_data[0]
                logger.info(f"Sample business: {sample.business_data.name}")
                logger.info(f"Lead score: {sample.lead_score}")
                logger.info(f"Customer insights: {sample.customer_insights}")
                
                # Test export functionality
                logger.info("Testing data export...")
                json_export = await pipeline.export_customer_360_data(customer_360_data[:3], "json")
                logger.info(f"JSON export length: {len(json_export)} characters")
                
                csv_export = await pipeline.export_customer_360_data(customer_360_data[:3], "csv")
                logger.info(f"CSV export length: {len(csv_export)} characters")
                logger.info("CSV preview:")
                print(csv_export[:500] + "..." if len(csv_export) > 500 else csv_export)
        
        # Test convenience functions
        logger.info("Testing convenience functions...")
        
        # Test lead report generation
        logger.info("Generating lead report...")
        lead_report = await generate_lead_report("hotel", "montego bay")
        logger.info(f"Lead report generated: {len(lead_report)} characters")
        
        logger.info("Unified pipeline testing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing unified pipeline: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_unified_pipeline())