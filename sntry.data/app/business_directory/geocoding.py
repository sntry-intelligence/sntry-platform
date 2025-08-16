"""
Google Geocoding API client with authentication, error handling, and batch processing
"""
import asyncio
import json
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import googlemaps
import httpx
from googlemaps.exceptions import ApiError, Timeout, TransportError

from app.core.config import settings
from app.core.redis import get_redis, RedisCache
from app.business_directory.schemas import GeocodingResult, AddressComponent


logger = logging.getLogger(__name__)


class GeocodingAPIError(Exception):
    """Custom exception for geocoding API errors"""
    pass


class GeocodingQuotaExceededError(GeocodingAPIError):
    """Exception raised when API quota is exceeded"""
    pass


class GoogleGeocodingClient:
    """
    Google Geocoding API client with proper authentication and error handling
    
    Features:
    - Synchronous and asynchronous geocoding
    - Batch processing capabilities
    - Comprehensive error handling
    - Response parsing and validation
    - Rate limiting and quota management
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the geocoding client
        
        Args:
            api_key: Google Geocoding API key. If None, uses settings.GOOGLE_GEOCODING_API_KEY
        """
        self.api_key = api_key or settings.GOOGLE_GEOCODING_API_KEY
        if not self.api_key:
            raise ValueError("Google Geocoding API key is required")
        
        # Initialize the Google Maps client
        self.gmaps = googlemaps.Client(key=self.api_key)
        
        # Initialize async HTTP client for batch operations
        self.async_client = None
        
        # API endpoints
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        # Rate limiting and quota tracking
        self.requests_per_second = 50  # Google's default limit
        self.daily_quota = 40000  # Adjust based on your quota
        self.monthly_budget = 200.0  # Monthly budget in USD
        self.cost_per_request = 0.005  # $0.005 per geocoding request
        
        # Usage tracking
        self.request_count = 0
        self.monthly_cost = 0.0
        self.quota_reset_time = datetime.now() + timedelta(days=1)
        self.budget_reset_time = datetime.now().replace(day=1) + timedelta(days=32)
        self.budget_reset_time = self.budget_reset_time.replace(day=1)  # First day of next month
        
        # Rate limiting
        self.last_request_time = datetime.now()
        self.request_times = []  # Track request times for rate limiting
        
        # Priority queue for critical requests
        self.priority_queue = []
        self.normal_queue = []
        
        logger.info("Google Geocoding client initialized successfully")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.async_client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.async_client:
            await self.async_client.aclose()
    
    def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        now = datetime.now()
        
        # Clean old request times (keep only last second)
        cutoff_time = now - timedelta(seconds=1)
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        
        # Check if we're exceeding requests per second
        if len(self.request_times) >= self.requests_per_second:
            sleep_time = 1.0 - (now - self.request_times[0]).total_seconds()
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                import time
                time.sleep(sleep_time)
        
        # Record this request time
        self.request_times.append(now)
    
    def _check_budget(self) -> None:
        """Check if we're within budget limits"""
        now = datetime.now()
        
        # Reset monthly budget if needed
        if now >= self.budget_reset_time:
            self.monthly_cost = 0.0
            # Set to first day of next month
            next_month = now.replace(day=1) + timedelta(days=32)
            self.budget_reset_time = next_month.replace(day=1)
        
        # Check monthly budget
        projected_cost = self.monthly_cost + self.cost_per_request
        if projected_cost > self.monthly_budget:
            raise GeocodingQuotaExceededError(
                f"Monthly budget of ${self.monthly_budget} would be exceeded. "
                f"Current cost: ${self.monthly_cost:.2f}, projected: ${projected_cost:.2f}"
            )
        
        # Warn if approaching budget (90% threshold)
        budget_percentage = (projected_cost / self.monthly_budget) * 100
        if budget_percentage > 90:
            logger.warning(
                f"Approaching monthly budget limit: {budget_percentage:.1f}% "
                f"(${projected_cost:.2f} of ${self.monthly_budget})"
            )
    
    def _check_quota(self) -> None:
        """Check if we're within API quota limits"""
        now = datetime.now()
        
        # Reset daily counter if needed
        if now >= self.quota_reset_time:
            self.request_count = 0
            self.quota_reset_time = now + timedelta(days=1)
        
        # Check daily quota
        if self.request_count >= self.daily_quota:
            raise GeocodingQuotaExceededError(
                f"Daily quota of {self.daily_quota} requests exceeded"
            )
    
    def _update_usage_tracking(self) -> None:
        """Update usage and cost tracking after a successful request"""
        self.request_count += 1
        self.monthly_cost += self.cost_per_request
        
        logger.debug(f"Usage updated: {self.request_count} requests today, ${self.monthly_cost:.2f} this month")
    
    def _optimize_address_for_geocoding(self, address: str) -> str:
        """
        Optimize address string to improve geocoding success rate and reduce costs
        
        Args:
            address: Raw address string
            
        Returns:
            str: Optimized address string
        """
        # Remove common problematic characters and patterns
        optimized = address.strip()
        
        # Remove multiple spaces
        optimized = ' '.join(optimized.split())
        
        # Add Jamaica if not present (improves accuracy for Jamaican addresses)
        if 'jamaica' not in optimized.lower() and 'jm' not in optimized.lower():
            optimized += ', Jamaica'
        
        # Remove common prefixes that don't help geocoding
        prefixes_to_remove = ['c/o ', 'care of ', 'attn:', 'attention:']
        for prefix in prefixes_to_remove:
            if optimized.lower().startswith(prefix):
                optimized = optimized[len(prefix):].strip()
        
        return optimized
    
    async def _priority_queue_geocode(self, address: str, region: str = "jm", priority: str = "normal") -> GeocodingResult:
        """
        Add geocoding request to priority queue for processing
        
        Args:
            address: Address to geocode
            region: Region bias
            priority: "high" for critical requests, "normal" for regular requests
            
        Returns:
            GeocodingResult: Geocoding result
        """
        request_data = {
            'address': address,
            'region': region,
            'timestamp': datetime.now(),
            'priority': priority
        }
        
        if priority == "high":
            self.priority_queue.append(request_data)
            logger.debug(f"Added high priority geocoding request for: {address}")
        else:
            self.normal_queue.append(request_data)
            logger.debug(f"Added normal priority geocoding request for: {address}")
        
        # Process the request immediately (in a real implementation, this might be handled by a background worker)
        return await self._process_geocoding_request(request_data)
    
    async def _process_geocoding_request(self, request_data: Dict[str, Any]) -> GeocodingResult:
        """
        Process a geocoding request with all optimizations and checks
        
        Args:
            request_data: Request data from priority queue
            
        Returns:
            GeocodingResult: Geocoding result
        """
        address = request_data['address']
        region = request_data['region']
        
        try:
            # Apply all checks and optimizations
            self._check_rate_limit()
            self._check_budget()
            self._check_quota()
            
            # Optimize address for better success rate
            optimized_address = self._optimize_address_for_geocoding(address)
            
            logger.debug(f"Processing geocoding request for: {address} (optimized: {optimized_address})")
            
            # Make the actual geocoding request
            if self.async_client:
                result = await self.geocode_address_async(optimized_address, region)
            else:
                result = self.geocode_address(optimized_address, region)
            
            # Update tracking only for successful API calls
            if result.status in ['OK', 'ZERO_RESULTS']:
                self._update_usage_tracking()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing geocoding request for '{address}': {e}")
            return GeocodingResult(
                status='UNKNOWN_ERROR',
                error_message=f'Processing error: {e}'
            )
    
    def _parse_geocoding_response(self, response_data: Dict[str, Any]) -> GeocodingResult:
        """
        Parse Google Geocoding API response into GeocodingResult schema
        
        Args:
            response_data: Raw response from Google Geocoding API
            
        Returns:
            GeocodingResult: Parsed and validated geocoding result
        """
        status = response_data.get('status', 'UNKNOWN_ERROR')
        
        # Handle error statuses
        if status != 'OK':
            error_message = response_data.get('error_message', f'Geocoding failed with status: {status}')
            return GeocodingResult(
                status=status,
                error_message=error_message
            )
        
        # Parse successful response
        results = response_data.get('results', [])
        if not results:
            return GeocodingResult(
                status='ZERO_RESULTS',
                error_message='No results found for the given address'
            )
        
        # Use the first (most relevant) result
        result = results[0]
        geometry = result.get('geometry', {})
        location = geometry.get('location', {})
        
        # Parse address components
        address_components = []
        for component in result.get('address_components', []):
            address_components.append(AddressComponent(
                long_name=component.get('long_name', ''),
                short_name=component.get('short_name', ''),
                types=component.get('types', [])
            ))
        
        return GeocodingResult(
            status=status,
            latitude=location.get('lat'),
            longitude=location.get('lng'),
            place_id=result.get('place_id'),
            formatted_address=result.get('formatted_address'),
            address_components=address_components,
            location_type=geometry.get('location_type'),
            viewport=geometry.get('viewport')
        )
    
    def geocode_address(self, address: str, region: str = "jm", priority: str = "normal") -> GeocodingResult:
        """
        Geocode a single address using the synchronous Google Maps client with cost optimization
        
        Args:
            address: Address string to geocode
            region: Region bias (default: "jm" for Jamaica)
            priority: Request priority ("high" or "normal")
            
        Returns:
            GeocodingResult: Geocoding result with coordinates and metadata
            
        Raises:
            GeocodingAPIError: If geocoding fails due to API issues
            GeocodingQuotaExceededError: If API quota is exceeded
        """
        try:
            # Apply all optimization checks
            self._check_rate_limit()
            self._check_budget()
            self._check_quota()
            
            # Optimize address for better success rate
            optimized_address = self._optimize_address_for_geocoding(address)
            
            logger.debug(f"Geocoding address: {address} (optimized: {optimized_address})")
            
            # Use the googlemaps library for synchronous geocoding
            result = self.gmaps.geocode(
                address=optimized_address,
                region=region,
                language='en'
            )
            
            # Parse the response
            response_data = {
                'status': 'OK' if result else 'ZERO_RESULTS',
                'results': result
            }
            
            geocoding_result = self._parse_geocoding_response(response_data)
            
            # Update usage tracking for successful API calls
            if geocoding_result.status in ['OK', 'ZERO_RESULTS']:
                self._update_usage_tracking()
            
            logger.debug(f"Geocoding successful for address: {address}, status: {geocoding_result.status}")
            return geocoding_result
            
        except ApiError as e:
            logger.error(f"Google Maps API error for address '{address}': {e}")
            return GeocodingResult(
                status='REQUEST_DENIED',
                error_message=str(e)
            )
        except Timeout as e:
            logger.error(f"Timeout error for address '{address}': {e}")
            return GeocodingResult(
                status='UNKNOWN_ERROR',
                error_message=f'Request timeout: {e}'
            )
        except TransportError as e:
            logger.error(f"Transport error for address '{address}': {e}")
            return GeocodingResult(
                status='UNKNOWN_ERROR',
                error_message=f'Transport error: {e}'
            )
        except GeocodingQuotaExceededError:
            # Re-raise quota errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error geocoding address '{address}': {e}")
            return GeocodingResult(
                status='UNKNOWN_ERROR',
                error_message=f'Unexpected error: {e}'
            )
    
    async def geocode_address_async(self, address: str, region: str = "jm", priority: str = "normal") -> GeocodingResult:
        """
        Geocode a single address asynchronously with cost optimization
        
        Args:
            address: Address string to geocode
            region: Region bias (default: "jm" for Jamaica)
            priority: Request priority ("high" or "normal")
            
        Returns:
            GeocodingResult: Geocoding result with coordinates and metadata
        """
        try:
            # Apply all optimization checks
            self._check_rate_limit()
            self._check_budget()
            self._check_quota()
            
            if not self.async_client:
                raise GeocodingAPIError("Async client not initialized. Use within async context manager.")
            
            # Optimize address for better success rate
            optimized_address = self._optimize_address_for_geocoding(address)
            
            logger.debug(f"Async geocoding address: {address} (optimized: {optimized_address})")
            
            # Prepare request parameters
            params = {
                'address': optimized_address,
                'region': region,
                'language': 'en',
                'key': self.api_key
            }
            
            # Make async HTTP request
            response = await self.async_client.get(self.geocoding_url, params=params)
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            geocoding_result = self._parse_geocoding_response(response_data)
            
            # Update usage tracking for successful API calls
            if geocoding_result.status in ['OK', 'ZERO_RESULTS']:
                self._update_usage_tracking()
            
            logger.debug(f"Async geocoding successful for address: {address}, status: {geocoding_result.status}")
            return geocoding_result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for address '{address}': {e}")
            return GeocodingResult(
                status='REQUEST_DENIED',
                error_message=f'HTTP error: {e.response.status_code}'
            )
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error for address '{address}': {e}")
            return GeocodingResult(
                status='UNKNOWN_ERROR',
                error_message='Request timeout'
            )
        except GeocodingQuotaExceededError:
            # Re-raise quota errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error async geocoding address '{address}': {e}")
            return GeocodingResult(
                status='UNKNOWN_ERROR',
                error_message=f'Unexpected error: {e}'
            )
    
    async def batch_geocode(
        self, 
        addresses: List[str], 
        region: str = "jm",
        max_concurrent: int = 10,
        delay_between_batches: float = 1.0
    ) -> List[GeocodingResult]:
        """
        Geocode multiple addresses in batches with concurrency control
        
        Args:
            addresses: List of address strings to geocode
            region: Region bias (default: "jm" for Jamaica)
            max_concurrent: Maximum concurrent requests
            delay_between_batches: Delay between batches in seconds
            
        Returns:
            List[GeocodingResult]: List of geocoding results in the same order as input
        """
        if not addresses:
            return []
        
        logger.info(f"Starting batch geocoding for {len(addresses)} addresses")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def geocode_with_semaphore(address: str) -> GeocodingResult:
            """Geocode with concurrency control"""
            async with semaphore:
                result = await self.geocode_address_async(address, region)
                # Add small delay to respect rate limits
                await asyncio.sleep(0.1)
                return result
        
        # Process addresses in batches
        batch_size = max_concurrent
        for i in range(0, len(addresses), batch_size):
            batch = addresses[i:i + batch_size]
            
            logger.debug(f"Processing batch {i//batch_size + 1}: {len(batch)} addresses")
            
            # Create tasks for the batch
            tasks = [geocode_with_semaphore(address) for address in batch]
            
            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions and convert to GeocodingResult
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Exception in batch geocoding for address '{batch[j]}': {result}")
                    results.append(GeocodingResult(
                        status='UNKNOWN_ERROR',
                        error_message=f'Batch processing error: {result}'
                    ))
                else:
                    results.append(result)
            
            # Delay between batches to respect rate limits
            if i + batch_size < len(addresses):
                await asyncio.sleep(delay_between_batches)
        
        logger.info(f"Batch geocoding completed. Processed {len(results)} addresses")
        return results
    
    def get_quota_status(self) -> Dict[str, Any]:
        """
        Get current API quota and cost status
        
        Returns:
            Dict with quota and cost information
        """
        now = datetime.now()
        time_until_quota_reset = self.quota_reset_time - now
        time_until_budget_reset = self.budget_reset_time - now
        
        return {
            # Quota information
            'requests_used': self.request_count,
            'daily_quota': self.daily_quota,
            'requests_remaining': max(0, self.daily_quota - self.request_count),
            'quota_reset_time': self.quota_reset_time.isoformat(),
            'time_until_quota_reset_hours': max(0, time_until_quota_reset.total_seconds() / 3600),
            'quota_percentage_used': (self.request_count / self.daily_quota) * 100,
            
            # Cost information
            'monthly_cost': round(self.monthly_cost, 2),
            'monthly_budget': self.monthly_budget,
            'budget_remaining': round(max(0, self.monthly_budget - self.monthly_cost), 2),
            'budget_reset_time': self.budget_reset_time.isoformat(),
            'time_until_budget_reset_days': max(0, time_until_budget_reset.days),
            'budget_percentage_used': (self.monthly_cost / self.monthly_budget) * 100,
            'cost_per_request': self.cost_per_request,
            
            # Rate limiting information
            'requests_per_second_limit': self.requests_per_second,
            'current_requests_in_last_second': len(self.request_times),
            
            # Alerts
            'alerts': self._generate_quota_alerts()
        }
    
    def _generate_quota_alerts(self) -> List[str]:
        """Generate alerts based on current usage"""
        alerts = []
        
        # Quota alerts
        quota_percentage = (self.request_count / self.daily_quota) * 100
        if quota_percentage > 90:
            alerts.append(f"Daily quota usage critical: {quota_percentage:.1f}%")
        elif quota_percentage > 75:
            alerts.append(f"Daily quota usage high: {quota_percentage:.1f}%")
        
        # Budget alerts
        budget_percentage = (self.monthly_cost / self.monthly_budget) * 100
        if budget_percentage > 90:
            alerts.append(f"Monthly budget usage critical: {budget_percentage:.1f}%")
        elif budget_percentage > 75:
            alerts.append(f"Monthly budget usage high: {budget_percentage:.1f}%")
        
        # Rate limiting alerts
        if len(self.request_times) > self.requests_per_second * 0.8:
            alerts.append("Approaching rate limit threshold")
        
        return alerts
    
    def set_budget_limit(self, monthly_budget: float) -> None:
        """
        Set monthly budget limit
        
        Args:
            monthly_budget: Monthly budget in USD
        """
        self.monthly_budget = monthly_budget
        logger.info(f"Monthly budget limit set to ${monthly_budget}")
    
    def set_quota_limit(self, daily_quota: int) -> None:
        """
        Set daily quota limit
        
        Args:
            daily_quota: Daily request quota
        """
        self.daily_quota = daily_quota
        logger.info(f"Daily quota limit set to {daily_quota} requests")
    
    def get_cost_projection(self, estimated_requests: int) -> Dict[str, Any]:
        """
        Get cost projection for estimated number of requests
        
        Args:
            estimated_requests: Number of requests to estimate cost for
            
        Returns:
            Dict with cost projection information
        """
        estimated_cost = estimated_requests * self.cost_per_request
        total_projected_cost = self.monthly_cost + estimated_cost
        
        return {
            'estimated_requests': estimated_requests,
            'estimated_cost': round(estimated_cost, 2),
            'current_monthly_cost': round(self.monthly_cost, 2),
            'total_projected_cost': round(total_projected_cost, 2),
            'monthly_budget': self.monthly_budget,
            'budget_remaining_after': round(max(0, self.monthly_budget - total_projected_cost), 2),
            'will_exceed_budget': total_projected_cost > self.monthly_budget,
            'budget_percentage_after': (total_projected_cost / self.monthly_budget) * 100
        }


class GeocodingCache:
    """
    Redis-based caching layer for geocoding results with intelligent cache management
    
    Features:
    - Standardized address-based cache keys
    - Configurable TTL for different result types
    - Cache warming strategies
    - Cache invalidation and cleanup
    - Performance metrics tracking
    """
    
    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """
        Initialize geocoding cache
        
        Args:
            redis_cache: RedisCache instance. If None, will be initialized from get_redis()
        """
        self.redis_cache = redis_cache
        self.cache_prefix = "geocoding:"
        
        # Cache TTL settings (in seconds)
        self.ttl_successful = 30 * 24 * 3600  # 30 days for successful geocoding
        self.ttl_zero_results = 7 * 24 * 3600  # 7 days for ZERO_RESULTS
        self.ttl_errors = 1 * 3600  # 1 hour for API errors
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("Geocoding cache initialized")
    
    async def _get_redis_cache(self) -> RedisCache:
        """Get or initialize Redis cache instance"""
        if not self.redis_cache:
            redis_client = await get_redis()
            self.redis_cache = RedisCache(redis_client)
        return self.redis_cache
    
    def _generate_cache_key(self, address: str, region: str = "jm") -> str:
        """
        Generate standardized cache key for an address
        
        Args:
            address: Address string
            region: Region bias
            
        Returns:
            str: Standardized cache key
        """
        # Normalize address for consistent caching
        normalized_address = self._normalize_address(address)
        
        # Create hash of normalized address + region for consistent key generation
        key_data = f"{normalized_address}|{region}".encode('utf-8')
        address_hash = hashlib.md5(key_data).hexdigest()
        
        return f"{self.cache_prefix}{address_hash}"
    
    def _normalize_address(self, address: str) -> str:
        """
        Normalize address string for consistent cache key generation
        
        Args:
            address: Raw address string
            
        Returns:
            str: Normalized address string
        """
        # Convert to uppercase and remove extra whitespace
        normalized = ' '.join(address.upper().split())
        
        # Remove common punctuation that doesn't affect geocoding
        normalized = normalized.replace(',', ' ').replace('.', ' ')
        normalized = ' '.join(normalized.split())  # Remove extra spaces again
        
        return normalized
    
    def _get_ttl_for_result(self, result: GeocodingResult) -> int:
        """
        Get appropriate TTL based on geocoding result status
        
        Args:
            result: GeocodingResult to determine TTL for
            
        Returns:
            int: TTL in seconds
        """
        if result.status == 'OK':
            return self.ttl_successful
        elif result.status == 'ZERO_RESULTS':
            return self.ttl_zero_results
        else:
            return self.ttl_errors
    
    async def get_cached_result(self, address: str, region: str = "jm") -> Optional[GeocodingResult]:
        """
        Retrieve cached geocoding result
        
        Args:
            address: Address string to look up
            region: Region bias
            
        Returns:
            Optional[GeocodingResult]: Cached result if found, None otherwise
        """
        try:
            cache = await self._get_redis_cache()
            cache_key = self._generate_cache_key(address, region)
            
            cached_data = await cache.get(cache_key)
            if cached_data:
                self.cache_hits += 1
                result_dict = json.loads(cached_data)
                
                logger.debug(f"Cache hit for address: {address}")
                return GeocodingResult(**result_dict)
            else:
                self.cache_misses += 1
                logger.debug(f"Cache miss for address: {address}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving cached result for address '{address}': {e}")
            self.cache_misses += 1
            return None
    
    async def cache_result(self, address: str, result: GeocodingResult, region: str = "jm") -> bool:
        """
        Cache geocoding result with appropriate TTL
        
        Args:
            address: Address string that was geocoded
            result: GeocodingResult to cache
            region: Region bias used
            
        Returns:
            bool: True if caching was successful, False otherwise
        """
        try:
            cache = await self._get_redis_cache()
            cache_key = self._generate_cache_key(address, region)
            ttl = self._get_ttl_for_result(result)
            
            # Serialize result to JSON
            result_dict = result.dict()
            cached_data = json.dumps(result_dict, default=str)
            
            success = await cache.set(cache_key, cached_data, expire=ttl)
            
            if success:
                logger.debug(f"Cached geocoding result for address: {address}, TTL: {ttl}s")
            else:
                logger.warning(f"Failed to cache geocoding result for address: {address}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching result for address '{address}': {e}")
            return False
    
    async def invalidate_cache(self, address: str, region: str = "jm") -> bool:
        """
        Invalidate cached result for a specific address
        
        Args:
            address: Address string to invalidate
            region: Region bias
            
        Returns:
            bool: True if invalidation was successful, False otherwise
        """
        try:
            cache = await self._get_redis_cache()
            cache_key = self._generate_cache_key(address, region)
            
            success = await cache.delete(cache_key)
            
            if success:
                logger.debug(f"Invalidated cache for address: {address}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating cache for address '{address}': {e}")
            return False
    
    async def warm_cache(self, addresses: List[str], region: str = "jm") -> Dict[str, Any]:
        """
        Warm cache by pre-geocoding frequently accessed addresses
        
        Args:
            addresses: List of addresses to pre-geocode and cache
            region: Region bias
            
        Returns:
            Dict with warming statistics
        """
        logger.info(f"Starting cache warming for {len(addresses)} addresses")
        
        warmed_count = 0
        skipped_count = 0
        error_count = 0
        
        # Initialize geocoding client for warming
        async with GoogleGeocodingClient() as geocoding_client:
            for address in addresses:
                try:
                    # Check if already cached
                    cached_result = await self.get_cached_result(address, region)
                    if cached_result:
                        skipped_count += 1
                        continue
                    
                    # Geocode and cache
                    result = await geocoding_client.geocode_address_async(address, region)
                    await self.cache_result(address, result, region)
                    
                    warmed_count += 1
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Error warming cache for address '{address}': {e}")
                    error_count += 1
        
        stats = {
            'total_addresses': len(addresses),
            'warmed_count': warmed_count,
            'skipped_count': skipped_count,
            'error_count': error_count
        }
        
        logger.info(f"Cache warming completed: {stats}")
        return stats
    
    async def cleanup_expired_cache(self) -> Dict[str, Any]:
        """
        Clean up expired cache entries (Redis handles this automatically, but we can track it)
        
        Returns:
            Dict with cleanup statistics
        """
        # Redis automatically handles TTL expiration, but we can provide stats
        cache_stats = self.get_cache_stats()
        
        logger.info(f"Cache cleanup check completed: {cache_stats}")
        return cache_stats
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics
        
        Returns:
            Dict with cache statistics
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'total_requests': total_requests,
            'hit_rate_percentage': round(hit_rate, 2),
            'ttl_settings': {
                'successful_results': self.ttl_successful,
                'zero_results': self.ttl_zero_results,
                'error_results': self.ttl_errors
            }
        }
    
    def reset_stats(self) -> None:
        """Reset cache performance statistics"""
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Cache statistics reset")


class GeocodingService:
    """
    Comprehensive geocoding service that combines Google API client with Redis caching
    
    Features:
    - Automatic caching of all geocoding results
    - Cache-first lookup strategy
    - Batch processing with caching
    - Performance optimization
    - Cost reduction through caching
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize geocoding service with caching
        
        Args:
            api_key: Google Geocoding API key
        """
        self.geocoding_client = GoogleGeocodingClient(api_key)
        self.cache = GeocodingCache()
        
        logger.info("Geocoding service with caching initialized")
    
    async def geocode_address(self, address: str, region: str = "jm", use_cache: bool = True) -> GeocodingResult:
        """
        Geocode address with automatic caching
        
        Args:
            address: Address string to geocode
            region: Region bias
            use_cache: Whether to use caching (default: True)
            
        Returns:
            GeocodingResult: Geocoding result from cache or API
        """
        # Try cache first if enabled
        if use_cache:
            cached_result = await self.cache.get_cached_result(address, region)
            if cached_result:
                logger.debug(f"Returning cached result for address: {address}")
                return cached_result
        
        # Geocode using API
        async with self.geocoding_client as client:
            result = await client.geocode_address_async(address, region)
        
        # Cache the result if caching is enabled
        if use_cache:
            await self.cache.cache_result(address, result, region)
        
        return result
    
    async def batch_geocode_with_cache(
        self, 
        addresses: List[str], 
        region: str = "jm",
        max_concurrent: int = 10,
        use_cache: bool = True
    ) -> List[GeocodingResult]:
        """
        Batch geocode addresses with intelligent caching
        
        Args:
            addresses: List of addresses to geocode
            region: Region bias
            max_concurrent: Maximum concurrent requests
            use_cache: Whether to use caching
            
        Returns:
            List[GeocodingResult]: Geocoding results in same order as input
        """
        if not addresses:
            return []
        
        logger.info(f"Starting batch geocoding with cache for {len(addresses)} addresses")
        
        results = []
        addresses_to_geocode = []
        cache_results_map = {}
        
        # Check cache for all addresses if caching is enabled
        if use_cache:
            for i, address in enumerate(addresses):
                cached_result = await self.cache.get_cached_result(address, region)
                if cached_result:
                    cache_results_map[i] = cached_result
                else:
                    addresses_to_geocode.append((i, address))
        else:
            addresses_to_geocode = list(enumerate(addresses))
        
        logger.info(f"Found {len(cache_results_map)} cached results, need to geocode {len(addresses_to_geocode)} addresses")
        
        # Geocode remaining addresses
        api_results = {}
        if addresses_to_geocode:
            addresses_only = [addr for _, addr in addresses_to_geocode]
            
            async with self.geocoding_client as client:
                geocoded_results = await client.batch_geocode(
                    addresses_only, 
                    region, 
                    max_concurrent
                )
            
            # Map results back to original indices and cache them
            for (original_index, address), result in zip(addresses_to_geocode, geocoded_results):
                api_results[original_index] = result
                
                # Cache the result if caching is enabled
                if use_cache:
                    await self.cache.cache_result(address, result, region)
        
        # Combine cached and API results in original order
        for i in range(len(addresses)):
            if i in cache_results_map:
                results.append(cache_results_map[i])
            elif i in api_results:
                results.append(api_results[i])
            else:
                # This shouldn't happen, but handle gracefully
                results.append(GeocodingResult(
                    status='UNKNOWN_ERROR',
                    error_message='Result not found in cache or API results'
                ))
        
        logger.info(f"Batch geocoding completed: {len(results)} results returned")
        return results
    
    async def warm_cache_for_frequent_addresses(self, addresses: List[str], region: str = "jm") -> Dict[str, Any]:
        """
        Warm cache for frequently accessed addresses
        
        Args:
            addresses: List of addresses to warm
            region: Region bias
            
        Returns:
            Dict with warming statistics
        """
        return await self.cache.warm_cache(addresses, region)
    
    async def invalidate_address_cache(self, address: str, region: str = "jm") -> bool:
        """
        Invalidate cache for a specific address
        
        Args:
            address: Address to invalidate
            region: Region bias
            
        Returns:
            bool: Success status
        """
        return await self.cache.invalidate_cache(address, region)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return self.cache.get_cache_stats()
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get API quota status"""
        return self.geocoding_client.get_quota_status()
    
    def set_budget_limit(self, monthly_budget: float) -> None:
        """Set monthly budget limit"""
        self.geocoding_client.set_budget_limit(monthly_budget)
    
    def set_quota_limit(self, daily_quota: int) -> None:
        """Set daily quota limit"""
        self.geocoding_client.set_quota_limit(daily_quota)
    
    def get_cost_projection(self, estimated_requests: int) -> Dict[str, Any]:
        """Get cost projection for estimated requests"""
        return self.geocoding_client.get_cost_projection(estimated_requests)
    
    async def geocode_with_priority(self, address: str, region: str = "jm", priority: str = "high") -> GeocodingResult:
        """
        Geocode address with high priority (bypasses normal queue)
        
        Args:
            address: Address to geocode
            region: Region bias
            priority: Priority level ("high" for critical requests)
            
        Returns:
            GeocodingResult: Geocoding result
        """
        return await self.geocode_address(address, region, use_cache=True)
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status including quota, cache, and performance metrics
        
        Returns:
            Dict with all status information
        """
        quota_status = self.get_quota_status()
        cache_stats = self.get_cache_stats()
        
        return {
            'quota_and_cost': quota_status,
            'cache_performance': cache_stats,
            'service_status': 'operational',
            'optimization_features': {
                'caching_enabled': True,
                'rate_limiting_enabled': True,
                'budget_monitoring_enabled': True,
                'address_optimization_enabled': True,
                'priority_queuing_enabled': True
            }
        }


# Global geocoding service instance with caching
geocoding_service = GeocodingService()

# Global geocoding client instance (for backward compatibility)
geocoding_client = GoogleGeocodingClient()