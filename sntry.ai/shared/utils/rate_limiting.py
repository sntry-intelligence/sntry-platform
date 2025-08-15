import time
from typing import Optional
import redis.asyncio as redis
from fastapi import HTTPException, status, Request
from shared.config import get_settings
from shared.database import get_redis

settings = get_settings()


class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, requests: int = None, window: int = None):
        self.requests = requests or settings.rate_limit_requests
        self.window = window or settings.rate_limit_window
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed under rate limit"""
        async with get_redis() as redis_client:
            current_time = int(time.time())
            window_start = current_time - self.window
            
            # Use sliding window log algorithm
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            if current_requests >= self.requests:
                return False, {
                    "allowed": False,
                    "limit": self.requests,
                    "remaining": 0,
                    "reset_time": window_start + self.window
                }
            
            return True, {
                "allowed": True,
                "limit": self.requests,
                "remaining": self.requests - current_requests - 1,
                "reset_time": window_start + self.window
            }


async def rate_limit_middleware(request: Request, rate_limiter: RateLimiter = None):
    """Rate limiting middleware"""
    if not rate_limiter:
        rate_limiter = RateLimiter()
    
    # Use client IP as key (in production, consider user ID)
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    allowed, info = await rate_limiter.is_allowed(key)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset_time"])
            }
        )
    
    # Add rate limit headers to response
    request.state.rate_limit_headers = {
        "X-RateLimit-Limit": str(info["limit"]),
        "X-RateLimit-Remaining": str(info["remaining"]),
        "X-RateLimit-Reset": str(info["reset_time"])
    }