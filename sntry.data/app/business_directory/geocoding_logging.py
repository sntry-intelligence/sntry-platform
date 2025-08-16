"""
Logging utilities for geocoding operations with cost and quota monitoring
"""
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from config.logging import get_geocoding_logger

logger = get_geocoding_logger()


@dataclass
class GeocodingMetrics:
    """Metrics for geocoding operations"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    zero_results: int = 0
    over_query_limit: int = 0
    invalid_requests: int = 0
    unknown_errors: int = 0
    total_cost_usd: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        total_cache_requests = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0


class GeocodingLogger:
    """Specialized logger for geocoding operations with cost tracking"""
    
    # Google Geocoding API pricing (as of 2024)
    COST_PER_REQUEST = 0.005  # $0.005 per request
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or "unknown"
        self.start_time = time.time()
        self.metrics = GeocodingMetrics()
    
    def log_geocoding_request(self, address: str, from_cache: bool = False):
        """Log geocoding request start"""
        self.metrics.total_requests += 1
        
        if from_cache:
            self.metrics.cache_hits += 1
        else:
            self.metrics.cache_misses += 1
            self.metrics.total_cost_usd += self.COST_PER_REQUEST
        
        logger.info(
            f"Geocoding request: {address}",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "address": address,
                    "from_cache": from_cache,
                    "request_cost_usd": 0.0 if from_cache else self.COST_PER_REQUEST,
                    "total_cost_usd": self.metrics.total_cost_usd,
                    "event_type": "geocoding_request"
                }
            }
        )
    
    def log_geocoding_success(self, address: str, lat: float, lng: float, place_id: str, **kwargs):
        """Log successful geocoding"""
        self.metrics.successful_requests += 1
        
        logger.info(
            f"Geocoding successful: {address}",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "address": address,
                    "latitude": lat,
                    "longitude": lng,
                    "place_id": place_id,
                    "success_rate": self.metrics.success_rate,
                    "event_type": "geocoding_success",
                    **kwargs
                }
            }
        )
    
    def log_geocoding_failure(self, address: str, status: str, error_message: str = None, **kwargs):
        """Log geocoding failure"""
        self.metrics.failed_requests += 1
        
        # Categorize the failure
        if status == "ZERO_RESULTS":
            self.metrics.zero_results += 1
        elif status == "OVER_QUERY_LIMIT":
            self.metrics.over_query_limit += 1
        elif status == "INVALID_REQUEST":
            self.metrics.invalid_requests += 1
        else:
            self.metrics.unknown_errors += 1
        
        logger.warning(
            f"Geocoding failed: {address} - {status}",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "address": address,
                    "status": status,
                    "error_message": error_message,
                    "failure_type": status,
                    "success_rate": self.metrics.success_rate,
                    "event_type": "geocoding_failure",
                    **kwargs
                }
            }
        )
    
    def log_quota_warning(self, current_usage: int, quota_limit: int, **kwargs):
        """Log quota usage warning"""
        usage_percentage = (current_usage / quota_limit * 100) if quota_limit > 0 else 0
        
        logger.warning(
            f"Geocoding quota usage warning: {usage_percentage:.1f}%",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "current_usage": current_usage,
                    "quota_limit": quota_limit,
                    "usage_percentage": usage_percentage,
                    "remaining_quota": quota_limit - current_usage,
                    "event_type": "quota_warning",
                    **kwargs
                }
            }
        )
    
    def log_cost_alert(self, daily_cost: float, monthly_cost: float, budget_limit: float, **kwargs):
        """Log cost alert when approaching budget limits"""
        budget_usage = (monthly_cost / budget_limit * 100) if budget_limit > 0 else 0
        
        log_level = logger.error if budget_usage >= 90 else logger.warning
        
        log_level(
            f"Geocoding cost alert: ${monthly_cost:.2f} (${daily_cost:.2f} today)",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "daily_cost_usd": daily_cost,
                    "monthly_cost_usd": monthly_cost,
                    "budget_limit_usd": budget_limit,
                    "budget_usage_percentage": budget_usage,
                    "remaining_budget_usd": budget_limit - monthly_cost,
                    "event_type": "cost_alert",
                    **kwargs
                }
            }
        )
    
    def log_batch_geocoding_start(self, batch_size: int, **kwargs):
        """Log batch geocoding start"""
        estimated_cost = batch_size * self.COST_PER_REQUEST
        
        logger.info(
            f"Batch geocoding started: {batch_size} addresses",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "batch_size": batch_size,
                    "estimated_cost_usd": estimated_cost,
                    "event_type": "batch_geocoding_start",
                    **kwargs
                }
            }
        )
    
    def log_batch_geocoding_complete(self, **kwargs):
        """Log batch geocoding completion with metrics"""
        duration = time.time() - self.start_time
        
        logger.info(
            f"Batch geocoding completed",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "duration_seconds": round(duration, 2),
                    "metrics": {
                        "total_requests": self.metrics.total_requests,
                        "successful_requests": self.metrics.successful_requests,
                        "failed_requests": self.metrics.failed_requests,
                        "success_rate": self.metrics.success_rate,
                        "zero_results": self.metrics.zero_results,
                        "over_query_limit": self.metrics.over_query_limit,
                        "total_cost_usd": self.metrics.total_cost_usd,
                        "cache_hit_rate": self.metrics.cache_hit_rate
                    },
                    "event_type": "batch_geocoding_complete",
                    **kwargs
                }
            }
        )
    
    def log_cache_performance(self, cache_size: int, cache_memory_mb: float, **kwargs):
        """Log cache performance metrics"""
        logger.info(
            f"Geocoding cache performance",
            extra={
                "extra_fields": {
                    "session_id": self.session_id,
                    "cache_size": cache_size,
                    "cache_memory_mb": cache_memory_mb,
                    "cache_hit_rate": self.metrics.cache_hit_rate,
                    "cache_hits": self.metrics.cache_hits,
                    "cache_misses": self.metrics.cache_misses,
                    "event_type": "cache_performance",
                    **kwargs
                }
            }
        )


def log_address_quality_analysis(addresses: List[str], parsed_addresses: List[dict]):
    """Log address quality analysis before geocoding"""
    if not addresses:
        return
    
    total = len(addresses)
    complete_addresses = sum(1 for addr in parsed_addresses if addr.get('street_name') and addr.get('city'))
    po_box_only = sum(1 for addr in parsed_addresses if addr.get('po_box') and not addr.get('street_name'))
    missing_components = sum(1 for addr in parsed_addresses if not addr.get('city'))
    
    logger.info(
        f"Address quality analysis before geocoding",
        extra={
            "extra_fields": {
                "total_addresses": total,
                "complete_addresses": complete_addresses,
                "complete_address_rate": round(complete_addresses / total * 100, 2),
                "po_box_only": po_box_only,
                "missing_components": missing_components,
                "event_type": "address_quality_analysis"
            }
        }
    )


def log_geocoding_rate_limit(retry_after: int, current_qps: float, **kwargs):
    """Log rate limiting events"""
    logger.warning(
        f"Geocoding rate limit hit, backing off for {retry_after}s",
        extra={
            "extra_fields": {
                "retry_after_seconds": retry_after,
                "current_qps": current_qps,
                "event_type": "rate_limit",
                **kwargs
            }
        }
    )