"""
Business Directory background tasks for scraping and data processing
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from celery import current_task
from celery.exceptions import Retry

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.business_directory.scraping.scraping_service import ScrapingService
from app.business_directory.repository import BusinessRepository
from app.business_directory.schemas import BusinessCreate
from app.business_directory.data_processing import DataProcessor

logger = logging.getLogger(__name__)

# Common business categories for Jamaica
JAMAICA_BUSINESS_CATEGORIES = [
    "restaurant", "hotel", "bank", "pharmacy", "supermarket", "gas_station",
    "auto_repair", "doctor", "dentist", "lawyer", "real_estate", "construction",
    "beauty_salon", "barber_shop", "clothing_store", "electronics", "furniture",
    "hardware_store", "insurance", "accounting", "travel_agency", "car_rental"
]

# Jamaica locations/parishes
JAMAICA_LOCATIONS = [
    "kingston", "spanish_town", "portmore", "montego_bay", "mandeville",
    "may_pen", "old_harbour", "savanna_la_mar", "port_antonio", "ocho_rios",
    "linstead", "half_way_tree", "new_kingston", "downtown_kingston"
]


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_full_website(self, websites: Optional[List[str]] = None):
    """
    Full website scraping task for comprehensive data collection
    Scrapes all categories from all supported websites
    """
    try:
        if websites is None:
            websites = ["findyello", "workandjam"]
        
        logger.info(f"Starting full website scraping for: {websites}")
        
        total_businesses = 0
        new_businesses = 0
        updated_businesses = 0
        errors = []
        
        # Run async scraping in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async with ScrapingService(headless=True) as scraping_service:
                # Scrape all categories
                for category in JAMAICA_BUSINESS_CATEGORIES:
                    try:
                        logger.info(f"Scraping category: {category}")
                        
                        # Update task progress
                        current_task.update_state(
                            state='PROGRESS',
                            meta={
                                'current_category': category,
                                'total_categories': len(JAMAICA_BUSINESS_CATEGORIES),
                                'businesses_found': total_businesses
                            }
                        )
                        
                        businesses = await scraping_service.scrape_category(
                            category=category,
                            location="",  # Search all locations
                            websites=websites
                        )
                        
                        # Process and save businesses
                        if businesses:
                            saved_count, new_count = await _process_and_save_businesses(businesses)
                            total_businesses += len(businesses)
                            new_businesses += new_count
                            updated_businesses += (saved_count - new_count)
                        
                        # Add delay between categories
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        error_msg = f"Error scraping category {category}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
        
        finally:
            loop.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "websites": websites,
            "total_businesses_scraped": total_businesses,
            "new_businesses": new_businesses,
            "updated_businesses": updated_businesses,
            "categories_processed": len(JAMAICA_BUSINESS_CATEGORIES),
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Full website scraping completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Full website scraping failed: {e}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying full website scraping (attempt {self.request.retries + 1})")
            raise self.retry(countdown=300 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e),
            "retries": self.request.retries
        }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=180)
def daily_scraping_task(self):
    """
    Daily scraping task for incremental updates
    Focuses on recently updated or new listings
    """
    try:
        logger.info("Starting daily incremental scraping task")
        
        # Select a subset of categories for daily updates
        daily_categories = JAMAICA_BUSINESS_CATEGORIES[:10]  # First 10 categories
        
        total_businesses = 0
        new_businesses = 0
        updated_businesses = 0
        errors = []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async with ScrapingService(headless=True) as scraping_service:
                for category in daily_categories:
                    try:
                        logger.info(f"Daily scraping category: {category}")
                        
                        businesses = await scraping_service.scrape_category(
                            category=category,
                            location="kingston",  # Focus on main city for daily updates
                            websites=["findyello", "workandjam"]
                        )
                        
                        if businesses:
                            saved_count, new_count = await _process_and_save_businesses(businesses)
                            total_businesses += len(businesses)
                            new_businesses += new_count
                            updated_businesses += (saved_count - new_count)
                        
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        error_msg = f"Error in daily scraping for {category}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
        
        finally:
            loop.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "type": "daily_incremental",
            "total_businesses_scraped": total_businesses,
            "new_businesses": new_businesses,
            "updated_businesses": updated_businesses,
            "categories_processed": len(daily_categories),
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Daily scraping task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Daily scraping task failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=180 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def incremental_scraping_task(self):
    """
    Incremental scraping task for regular updates
    Runs every 4 hours to catch new listings
    """
    try:
        logger.info("Starting incremental scraping task")
        
        # Rotate through different categories each run
        current_hour = datetime.now().hour
        category_index = current_hour % len(JAMAICA_BUSINESS_CATEGORIES)
        selected_categories = JAMAICA_BUSINESS_CATEGORIES[category_index:category_index+3]
        
        total_businesses = 0
        new_businesses = 0
        errors = []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async with ScrapingService(headless=True) as scraping_service:
                for category in selected_categories:
                    try:
                        businesses = await scraping_service.scrape_category(
                            category=category,
                            location="",
                            websites=["findyello", "workandjam"]
                        )
                        
                        if businesses:
                            saved_count, new_count = await _process_and_save_businesses(businesses)
                            total_businesses += len(businesses)
                            new_businesses += new_count
                        
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        error_msg = f"Error in incremental scraping for {category}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
        
        finally:
            loop.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "type": "incremental",
            "categories_scraped": selected_categories,
            "total_businesses_scraped": total_businesses,
            "new_businesses": new_businesses,
            "errors": errors,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Incremental scraping task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Incremental scraping task failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def scrape_category_task(self, category: str, location: str = "", websites: Optional[List[str]] = None):
    """
    Scrape specific category of businesses
    Used for targeted data collection
    """
    try:
        if websites is None:
            websites = ["findyello", "workandjam"]
        
        logger.info(f"Starting category scraping: {category} in {location}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        businesses_found = 0
        new_businesses = 0
        
        try:
            async with ScrapingService(headless=True) as scraping_service:
                businesses = await scraping_service.scrape_category(
                    category=category,
                    location=location,
                    websites=websites
                )
                
                businesses_found = len(businesses)
                
                if businesses:
                    saved_count, new_count = await _process_and_save_businesses(businesses)
                    new_businesses = new_count
        
        finally:
            loop.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "category": category,
            "location": location,
            "websites": websites,
            "businesses_found": businesses_found,
            "new_businesses": new_businesses,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Category scraping completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Category scraping failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "category": category,
            "location": location,
            "error": str(e)
        }


@celery_app.task(bind=True)
def scrape_and_process_chain(self, category: str, location: str = ""):
    """
    Chained task: scraping followed by data processing and geocoding
    Demonstrates task chaining workflow
    """
    try:
        logger.info(f"Starting chained scraping and processing for {category}")
        
        # Step 1: Scrape data
        scrape_result = scrape_category_task.apply_async(
            args=[category, location],
            queue="scraping"
        ).get()
        
        if scrape_result["status"] != "completed":
            raise Exception(f"Scraping failed: {scrape_result.get('error', 'Unknown error')}")
        
        # Step 2: Trigger geocoding for new businesses
        if scrape_result["new_businesses"] > 0:
            from app.business_directory.tasks import batch_geocoding_task
            geocode_result = batch_geocoding_task.apply_async(
                queue="geocoding"
            ).get()
            
            result = {
                "task_id": self.request.id,
                "status": "completed",
                "scraping_result": scrape_result,
                "geocoding_result": geocode_result,
                "completed_at": datetime.utcnow().isoformat()
            }
        else:
            result = {
                "task_id": self.request.id,
                "status": "completed",
                "scraping_result": scrape_result,
                "geocoding_result": {"message": "No new businesses to geocode"},
                "completed_at": datetime.utcnow().isoformat()
            }
        
        logger.info(f"Chained task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Chained task failed: {e}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }


async def _process_and_save_businesses(businesses: List[Any]) -> tuple[int, int]:
    """
    Helper function to process and save scraped businesses
    Returns (total_saved, new_businesses)
    """
    if not businesses:
        return 0, 0
    
    saved_count = 0
    new_count = 0
    
    # Get database session
    db = next(get_db())
    repository = BusinessRepository(db)
    data_processor = DataProcessor()
    
    try:
        for business_data in businesses:
            try:
                # Convert to BusinessCreate schema
                business_create = BusinessCreate(
                    name=business_data.name,
                    category=business_data.category,
                    raw_address=business_data.raw_address,
                    phone_number=business_data.phone_number,
                    email=business_data.email,
                    website=business_data.website,
                    description=business_data.description,
                    operating_hours=business_data.operating_hours,
                    rating=business_data.rating,
                    source_url=business_data.source_url
                )
                
                # Check if business already exists (basic deduplication)
                existing = repository.search_by_name_and_address(
                    business_create.name,
                    business_create.raw_address
                )
                
                if existing:
                    # Update existing business
                    repository.update(existing.id, business_create)
                    saved_count += 1
                else:
                    # Create new business
                    repository.create(business_create)
                    saved_count += 1
                    new_count += 1
                
            except Exception as e:
                logger.error(f"Error saving business {business_data.name}: {e}")
                continue
    
    finally:
        db.close()
    
    return saved_count, new_count


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def batch_geocoding_task(self, limit: int = 50):
    """
    Batch geocoding task for processing un-geocoded addresses
    Processes businesses that need geocoding in batches
    """
    try:
        logger.info(f"Starting batch geocoding task for {limit} addresses")
        
        # Get database session
        db = next(get_db())
        repository = BusinessRepository(db)
        
        # Get businesses that need geocoding
        businesses_to_geocode = repository.get_pending_geocoding(limit=limit)
        
        if not businesses_to_geocode:
            logger.info("No businesses found that need geocoding")
            return {
                "task_id": self.request.id,
                "status": "completed",
                "message": "No businesses need geocoding",
                "addresses_processed": 0,
                "successful_geocodes": 0,
                "failed_geocodes": 0
            }
        
        addresses_processed = 0
        successful_geocodes = 0
        failed_geocodes = 0
        errors = []
        
        # Run async geocoding in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from app.business_directory.geocoding import GeocodingService
            
            async with GeocodingService() as geocoding_service:
                for business in businesses_to_geocode:
                    try:
                        # Update task progress
                        current_task.update_state(
                            state='PROGRESS',
                            meta={
                                'current_business': business.name,
                                'processed': addresses_processed,
                                'total': len(businesses_to_geocode)
                            }
                        )
                        
                        # Geocode the address
                        result = await geocoding_service.geocode_address(
                            address=business.raw_address,
                            region="jm",
                            use_cache=True
                        )
                        
                        addresses_processed += 1
                        
                        if result.status == "OK" and result.latitude and result.longitude:
                            # Update business with geocoding results
                            repository.update_geocoding_data(
                                business_id=business.id,
                                latitude=result.latitude,
                                longitude=result.longitude,
                                google_place_id=result.place_id,
                                formatted_address=result.formatted_address
                            )
                            successful_geocodes += 1
                            logger.info(f"Successfully geocoded: {business.name}")
                        else:
                            # Update geocoding status to failed
                            business.geocode_status = result.status or 'UNKNOWN_ERROR'
                            db.commit()
                            failed_geocodes += 1
                            logger.warning(f"Failed to geocode {business.name}: {result.status}")
                        
                        # Add delay to respect rate limits
                        await asyncio.sleep(0.1)  # 10 requests per second max
                        
                    except Exception as e:
                        error_msg = f"Error geocoding business {business.name}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        failed_geocodes += 1
                        
                        # Mark as failed in database
                        business.geocode_status = 'UNKNOWN_ERROR'
                        db.commit()
                        continue
        
        finally:
            loop.close()
            db.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "addresses_processed": addresses_processed,
            "successful_geocodes": successful_geocodes,
            "failed_geocodes": failed_geocodes,
            "success_rate": (successful_geocodes / addresses_processed * 100) if addresses_processed > 0 else 0,
            "errors": errors[:10],  # Limit error list
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Batch geocoding task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Batch geocoding task failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }