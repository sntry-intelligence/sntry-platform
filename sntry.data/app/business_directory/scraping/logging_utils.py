"""
Logging utilities for scraping operations
"""
import time
from typing import Dict, Any, Optional
from contextlib import contextmanager
from config.logging import get_scraping_logger

logger = get_scraping_logger()


class ScrapingLogger:
    """Specialized logger for scraping operations"""
    
    def __init__(self, scraper_name: str, session_id: Optional[str] = None):
        self.scraper_name = scraper_name
        self.session_id = session_id or "unknown"
        self.start_time = time.time()
        self.stats = {
            "pages_scraped": 0,
            "businesses_found": 0,
            "errors": 0,
            "retries": 0,
            "anti_bot_triggers": 0
        }
    
    def log_session_start(self, target_url: str, **kwargs):
        """Log scraping session start"""
        logger.info(
            f"Scraping session started for {self.scraper_name}",
            extra={
                "extra_fields": {
                    "scraper_name": self.scraper_name,
                    "session_id": self.session_id,
                    "target_url": target_url,
                    "event_type": "scraping_session_start",
                    **kwargs
                }
            }
        )
    
    def log_page_scraped(self, url: str, businesses_found: int, **kwargs):
        """Log successful page scraping"""
        self.stats["pages_scraped"] += 1
        self.stats["businesses_found"] += businesses_found
        
        logger.info(
            f"Page scraped successfully: {businesses_found} businesses found",
            extra={
                "extra_fields": {
                    "scraper_name": self.scraper_name,
                    "session_id": self.session_id,
                    "url": url,
                    "businesses_found": businesses_found,
                    "total_businesses": self.stats["businesses_found"],
                    "total_pages": self.stats["pages_scraped"],
                    "event_type": "page_scraped",
                    **kwargs
                }
            }
        )
    
    def log_error(self, error: Exception, url: str, **kwargs):
        """Log scraping error"""
        self.stats["errors"] += 1
        
        logger.error(
            f"Scraping error on {url}: {str(error)}",
            extra={
                "extra_fields": {
                    "scraper_name": self.scraper_name,
                    "session_id": self.session_id,
                    "url": url,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "total_errors": self.stats["errors"],
                    "event_type": "scraping_error",
                    **kwargs
                }
            },
            exc_info=True
        )
    
    def log_retry(self, url: str, attempt: int, reason: str, **kwargs):
        """Log retry attempt"""
        self.stats["retries"] += 1
        
        logger.warning(
            f"Retrying scraping attempt {attempt} for {url}: {reason}",
            extra={
                "extra_fields": {
                    "scraper_name": self.scraper_name,
                    "session_id": self.session_id,
                    "url": url,
                    "attempt": attempt,
                    "reason": reason,
                    "total_retries": self.stats["retries"],
                    "event_type": "scraping_retry",
                    **kwargs
                }
            }
        )
    
    def log_anti_bot_trigger(self, trigger_type: str, url: str, **kwargs):
        """Log anti-bot measure trigger"""
        self.stats["anti_bot_triggers"] += 1
        
        logger.warning(
            f"Anti-bot measure triggered: {trigger_type}",
            extra={
                "extra_fields": {
                    "scraper_name": self.scraper_name,
                    "session_id": self.session_id,
                    "url": url,
                    "trigger_type": trigger_type,
                    "total_anti_bot_triggers": self.stats["anti_bot_triggers"],
                    "event_type": "anti_bot_trigger",
                    **kwargs
                }
            }
        )
    
    def log_session_complete(self, success: bool = True, **kwargs):
        """Log scraping session completion"""
        duration = time.time() - self.start_time
        
        log_level = logger.info if success else logger.error
        status = "completed" if success else "failed"
        
        log_level(
            f"Scraping session {status} for {self.scraper_name}",
            extra={
                "extra_fields": {
                    "scraper_name": self.scraper_name,
                    "session_id": self.session_id,
                    "duration_seconds": round(duration, 2),
                    "success": success,
                    "stats": self.stats,
                    "event_type": "scraping_session_complete",
                    **kwargs
                }
            }
        )


@contextmanager
def scraping_session(scraper_name: str, target_url: str, session_id: Optional[str] = None):
    """Context manager for scraping sessions with automatic logging"""
    scraping_logger = ScrapingLogger(scraper_name, session_id)
    scraping_logger.log_session_start(target_url)
    
    try:
        yield scraping_logger
        scraping_logger.log_session_complete(success=True)
    except Exception as e:
        scraping_logger.log_session_complete(success=False, error=str(e))
        raise


def log_business_data_quality(businesses: list, scraper_name: str):
    """Log data quality metrics for scraped businesses"""
    if not businesses:
        return
    
    total = len(businesses)
    with_phone = sum(1 for b in businesses if getattr(b, 'phone_number', None))
    with_email = sum(1 for b in businesses if getattr(b, 'email', None))
    with_website = sum(1 for b in businesses if getattr(b, 'website', None))
    with_address = sum(1 for b in businesses if getattr(b, 'raw_address', None))
    
    logger.info(
        f"Data quality metrics for {scraper_name}",
        extra={
            "extra_fields": {
                "scraper_name": scraper_name,
                "total_businesses": total,
                "phone_coverage": round(with_phone / total * 100, 2),
                "email_coverage": round(with_email / total * 100, 2),
                "website_coverage": round(with_website / total * 100, 2),
                "address_coverage": round(with_address / total * 100, 2),
                "event_type": "data_quality_metrics"
            }
        }
    )