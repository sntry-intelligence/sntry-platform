"""
Redis configuration and connection management
"""
import redis.asyncio as redis
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis connection pool
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection pool"""
    global redis_pool, redis_client
    
    try:
        redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            retry_on_timeout=True,
            decode_responses=True
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Redis initialization failed: {e}")
        raise


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if not redis_client:
        await init_redis()
    return redis_client


async def close_redis():
    """Close Redis connections"""
    global redis_client, redis_pool
    
    if redis_client:
        await redis_client.close()
        redis_client = None
    
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
    
    logger.info("Redis connections closed")


class RedisCache:
    """Redis caching utility class"""
    
    def __init__(self, client: redis.Redis):
        self.client = client
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration"""
        try:
            return await self.client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(await self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False