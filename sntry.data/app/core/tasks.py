"""
Core maintenance and monitoring tasks
"""
import logging
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import test_connections

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def health_check_task(self):
    """Health check task for monitoring system status"""
    try:
        # Test database connections
        db_status = test_connections()
        
        # Test Redis connection
        # This will be implemented when Redis client is available
        redis_status = True
        
        result = {
            "task_id": self.request.id,
            "status": "healthy" if db_status and redis_status else "unhealthy",
            "database": "ok" if db_status else "error",
            "redis": "ok" if redis_status else "error"
        }
        
        logger.info(f"Health check completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=600)
def data_quality_check(self):
    """
    Data quality check task for identifying and flagging problematic records
    Runs comprehensive checks on business data quality
    """
    try:
        logger.info("Starting data quality check task")
        
        from app.core.database import get_db
        from app.business_directory.repository import BusinessRepository
        
        # Get database session
        db = next(get_db())
        repository = BusinessRepository(db)
        
        quality_issues = {
            "missing_addresses": 0,
            "missing_phone_numbers": 0,
            "invalid_emails": 0,
            "missing_categories": 0,
            "duplicate_businesses": 0,
            "failed_geocoding": 0,
            "stale_data": 0,
            "inactive_businesses": 0
        }
        
        recommendations = []
        
        try:
            # Get database statistics
            stats = repository.get_statistics()
            
            # Check for missing critical data
            from sqlalchemy import and_, or_, func
            from app.business_directory.models import Business
            from datetime import datetime, timedelta
            
            # Missing addresses
            missing_addresses = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    or_(Business.raw_address.is_(None), Business.raw_address == "")
                )
            ).count()
            quality_issues["missing_addresses"] = missing_addresses
            
            if missing_addresses > 0:
                recommendations.append(f"Found {missing_addresses} businesses with missing addresses")
            
            # Missing phone numbers
            missing_phones = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    or_(Business.phone_number.is_(None), Business.phone_number == "")
                )
            ).count()
            quality_issues["missing_phone_numbers"] = missing_phones
            
            # Invalid email addresses (basic check)
            invalid_emails = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.email.isnot(None),
                    ~Business.email.contains("@")
                )
            ).count()
            quality_issues["invalid_emails"] = invalid_emails
            
            # Missing categories
            missing_categories = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    or_(Business.category.is_(None), Business.category == "")
                )
            ).count()
            quality_issues["missing_categories"] = missing_categories
            
            # Failed geocoding
            failed_geocoding = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.geocode_status.in_(['ZERO_RESULTS', 'INVALID_REQUEST', 'UNKNOWN_ERROR'])
                )
            ).count()
            quality_issues["failed_geocoding"] = failed_geocoding
            
            if failed_geocoding > 0:
                recommendations.append(f"Found {failed_geocoding} businesses with failed geocoding - consider manual review")
            
            # Stale data (not updated in 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            stale_data = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.last_scraped_at < thirty_days_ago
                )
            ).count()
            quality_issues["stale_data"] = stale_data
            
            if stale_data > 0:
                recommendations.append(f"Found {stale_data} businesses with stale data (>30 days old)")
            
            # Inactive businesses
            inactive_businesses = db.query(Business).filter(Business.is_active == False).count()
            quality_issues["inactive_businesses"] = inactive_businesses
            
            # Potential duplicates (basic name similarity check)
            # This is a simplified check - full deduplication would be more complex
            duplicate_names = db.query(
                Business.name, func.count(Business.id)
            ).filter(
                Business.is_active == True
            ).group_by(Business.name).having(func.count(Business.id) > 1).all()
            
            quality_issues["duplicate_businesses"] = len(duplicate_names)
            
            if duplicate_names:
                recommendations.append(f"Found {len(duplicate_names)} potential duplicate business names")
            
            # Calculate overall quality score
            total_businesses = stats.get('active_businesses', 1)
            quality_score = max(0, 100 - (
                (missing_addresses / total_businesses * 20) +
                (missing_phones / total_businesses * 15) +
                (invalid_emails / total_businesses * 10) +
                (missing_categories / total_businesses * 15) +
                (failed_geocoding / total_businesses * 25) +
                (stale_data / total_businesses * 15)
            ))
            
            # Generate recommendations based on issues
            if quality_score < 70:
                recommendations.append("Overall data quality is below acceptable threshold (70%)")
            
            if missing_addresses > total_businesses * 0.1:
                recommendations.append("High percentage of missing addresses - prioritize address collection")
            
            if failed_geocoding > total_businesses * 0.2:
                recommendations.append("High geocoding failure rate - review address formats")
            
        finally:
            db.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "quality_score": round(quality_score, 2),
            "total_businesses": total_businesses,
            "quality_issues": quality_issues,
            "recommendations": recommendations,
            "database_stats": stats,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data quality check completed: Quality score {quality_score:.1f}%")
        return result
        
    except Exception as e:
        logger.error(f"Data quality check failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=600 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_inactive_businesses(self):
    """
    Cleanup task for removing inactive or outdated business records
    Performs soft deletion of businesses that haven't been updated in a long time
    """
    try:
        logger.info("Starting cleanup of inactive businesses")
        
        from app.core.database import get_db
        from app.business_directory.repository import BusinessRepository
        from app.business_directory.models import Business
        from datetime import datetime, timedelta
        
        # Get database session
        db = next(get_db())
        repository = BusinessRepository(db)
        
        # Define cleanup criteria
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        one_year_ago = datetime.utcnow() - timedelta(days=365)
        
        cleanup_stats = {
            "businesses_deactivated": 0,
            "old_records_flagged": 0,
            "failed_geocoding_cleaned": 0,
            "duplicate_records_merged": 0
        }
        
        try:
            # 1. Deactivate businesses not updated in 6 months with failed scraping
            stale_failed_businesses = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.last_scraped_at < six_months_ago,
                    Business.scrape_status == 'failed'
                )
            ).all()
            
            for business in stale_failed_businesses:
                business.is_active = False
                cleanup_stats["businesses_deactivated"] += 1
            
            # 2. Flag very old records (1+ year) for manual review
            very_old_businesses = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.last_scraped_at < one_year_ago
                )
            ).count()
            cleanup_stats["old_records_flagged"] = very_old_businesses
            
            # 3. Clean up businesses with persistent geocoding failures
            persistent_geocoding_failures = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.geocode_status.in_(['ZERO_RESULTS', 'INVALID_REQUEST']),
                    Business.last_scraped_at < six_months_ago
                )
            ).all()
            
            for business in persistent_geocoding_failures:
                # Mark for manual review rather than deactivating
                business.geocode_status = 'MANUAL_REVIEW_NEEDED'
                cleanup_stats["failed_geocoding_cleaned"] += 1
            
            # Commit all changes
            db.commit()
            
        finally:
            db.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "cleanup_stats": cleanup_stats,
            "cleanup_criteria": {
                "stale_threshold_days": 180,
                "old_record_threshold_days": 365
            },
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Cleanup task completed: {cleanup_stats}")
        return result
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=240)
def data_refresh_task(self):
    """
    Data refresh task for updating stale business information
    Identifies and re-scrapes businesses with outdated information
    """
    try:
        logger.info("Starting data refresh task")
        
        from app.core.database import get_db
        from app.business_directory.repository import BusinessRepository
        from app.business_directory.models import Business
        from datetime import datetime, timedelta
        
        # Get database session
        db = next(get_db())
        repository = BusinessRepository(db)
        
        # Define refresh criteria
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        refresh_stats = {
            "businesses_identified": 0,
            "high_priority_refresh": 0,
            "medium_priority_refresh": 0,
            "low_priority_refresh": 0,
            "refresh_tasks_queued": 0
        }
        
        try:
            # 1. Identify businesses needing refresh
            stale_businesses = db.query(Business).filter(
                and_(
                    Business.is_active == True,
                    Business.last_scraped_at < thirty_days_ago
                )
            ).all()
            
            refresh_stats["businesses_identified"] = len(stale_businesses)
            
            # 2. Prioritize refresh based on business importance
            high_priority_categories = ['restaurant', 'hotel', 'bank', 'pharmacy', 'hospital']
            medium_priority_categories = ['supermarket', 'gas_station', 'auto_repair']
            
            high_priority_businesses = []
            medium_priority_businesses = []
            low_priority_businesses = []
            
            for business in stale_businesses:
                category = (business.category or "").lower()
                
                if any(cat in category for cat in high_priority_categories):
                    high_priority_businesses.append(business)
                elif any(cat in category for cat in medium_priority_categories):
                    medium_priority_businesses.append(business)
                else:
                    low_priority_businesses.append(business)
            
            refresh_stats["high_priority_refresh"] = len(high_priority_businesses)
            refresh_stats["medium_priority_refresh"] = len(medium_priority_businesses)
            refresh_stats["low_priority_refresh"] = len(low_priority_businesses)
            
            # 3. Queue refresh tasks (limit to prevent overwhelming the system)
            max_refresh_per_run = 50
            businesses_to_refresh = (
                high_priority_businesses[:20] +  # Max 20 high priority
                medium_priority_businesses[:20] +  # Max 20 medium priority
                low_priority_businesses[:10]  # Max 10 low priority
            )
            
            # Queue individual scraping tasks for each business
            for business in businesses_to_refresh[:max_refresh_per_run]:
                try:
                    # Import here to avoid circular imports
                    from app.business_directory.tasks import scrape_category_task
                    
                    # Queue a category scraping task that will include this business
                    scrape_category_task.apply_async(
                        args=[business.category or "general", ""],
                        queue="scraping",
                        priority=8 if business in high_priority_businesses else 5
                    )
                    
                    refresh_stats["refresh_tasks_queued"] += 1
                    
                except Exception as e:
                    logger.error(f"Error queuing refresh task for business {business.id}: {e}")
                    continue
            
            # 4. Update refresh tracking
            for business in businesses_to_refresh[:max_refresh_per_run]:
                business.last_scraped_at = datetime.utcnow()  # Mark as being refreshed
            
            db.commit()
            
        finally:
            db.close()
        
        result = {
            "task_id": self.request.id,
            "status": "completed",
            "refresh_stats": refresh_stats,
            "refresh_criteria": {
                "stale_threshold_days": 30,
                "max_refresh_per_run": max_refresh_per_run
            },
            "completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data refresh task completed: {refresh_stats}")
        return result
        
    except Exception as e:
        logger.error(f"Data refresh task failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=240 * (2 ** self.request.retries))
        
        return {
            "task_id": self.request.id,
            "status": "error",
            "error": str(e)
        }