import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from datetime import datetime, timedelta
from prisma import Prisma
from prisma.models import Agent, Workflow, Tool, ConversationSession, VectorStore, MCPServer, Evaluation, User
import redis.asyncio as redis
from shared.config import get_settings

logger = logging.getLogger(__name__)

# Global database instances
db = Prisma()
redis_client = None


async def connect_database():
    """Connect to PostgreSQL database"""
    try:
        await db.connect()
        logger.info("Connected to PostgreSQL database")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise


async def disconnect_database():
    """Disconnect from PostgreSQL database"""
    try:
        await db.disconnect()
        logger.info("Disconnected from PostgreSQL database")
    except Exception as e:
        logger.error(f"Failed to disconnect from PostgreSQL: {e}")


async def connect_redis():
    """Connect to Redis cache"""
    global redis_client
    try:
        settings = get_settings()
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        # Test connection
        await redis_client.ping()
        logger.info("Connected to Redis cache")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None


async def disconnect_redis():
    """Disconnect from Redis cache"""
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Disconnected from Redis cache")
        except Exception as e:
            logger.error(f"Failed to disconnect from Redis: {e}")
        finally:
            redis_client = None


@asynccontextmanager
async def get_db() -> AsyncGenerator[Prisma, None]:
    """Get database connection context manager"""
    try:
        yield db
    finally:
        pass


@asynccontextmanager
async def get_redis() -> AsyncGenerator[Optional[redis.Redis], None]:
    """Get Redis connection context manager"""
    global redis_client
    try:
        yield redis_client
    finally:
        pass


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self):
        self.db = db
        self.redis_client = None
    
    async def startup(self):
        """Initialize database connections"""
        await connect_database()
        await connect_redis()
    
    async def shutdown(self):
        """Close database connections"""
        await disconnect_database()
        await disconnect_redis()


class CacheManager:
    """Redis cache management utilities"""
    
    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    cached_data = await redis_conn.get(key)
                    if cached_data:
                        return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    ttl = ttl or self.default_ttl
                    serialized_value = json.dumps(value, default=str)
                    await redis_conn.setex(key, ttl, serialized_value)
                    return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
        return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    result = await redis_conn.delete(key)
                    return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
        return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    keys = await redis_conn.keys(pattern)
                    if keys:
                        return await redis_conn.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache delete pattern error for {pattern}: {e}")
        return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    return await redis_conn.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
        return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    return await redis_conn.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
        return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    return await redis_conn.expire(key, ttl)
        except Exception as e:
            logger.warning(f"Cache expire error for key {key}: {e}")
        return False
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get TTL for key"""
        try:
            async with get_redis() as redis_conn:
                if redis_conn:
                    return await redis_conn.ttl(key)
        except Exception as e:
            logger.warning(f"Cache TTL error for key {key}: {e}")
        return None


class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        identifier: str = ""
    ) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit"""
        cache_key = f"rate_limit:{key}:{identifier}" if identifier else f"rate_limit:{key}"
        
        try:
            async with get_redis() as redis_conn:
                if not redis_conn:
                    # If Redis is not available, allow the request
                    return True, {"remaining": limit, "reset_time": None}
                
                # Use sliding window counter
                now = datetime.utcnow()
                window_start = now - timedelta(seconds=window)
                
                # Remove old entries
                await redis_conn.zremrangebyscore(
                    cache_key,
                    0,
                    window_start.timestamp()
                )
                
                # Count current requests
                current_count = await redis_conn.zcard(cache_key)
                
                if current_count >= limit:
                    # Get the oldest entry to determine reset time
                    oldest = await redis_conn.zrange(cache_key, 0, 0, withscores=True)
                    reset_time = None
                    if oldest:
                        reset_time = datetime.fromtimestamp(oldest[0][1]) + timedelta(seconds=window)
                    
                    return False, {
                        "remaining": 0,
                        "reset_time": reset_time,
                        "retry_after": window
                    }
                
                # Add current request
                await redis_conn.zadd(cache_key, {str(now.timestamp()): now.timestamp()})
                await redis_conn.expire(cache_key, window)
                
                return True, {
                    "remaining": limit - current_count - 1,
                    "reset_time": now + timedelta(seconds=window)
                }
                
        except Exception as e:
            logger.error(f"Rate limiter error for key {cache_key}: {e}")
            # On error, allow the request
            return True, {"remaining": limit, "reset_time": None}


class SessionManager:
    """Redis-based session management"""
    
    def __init__(self, cache_manager: CacheManager, default_ttl: int = 3600):
        self.cache = cache_manager
        self.default_ttl = default_ttl
    
    async def create_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Create a new session"""
        key = f"session:{session_id}"
        return await self.cache.set(key, data, ttl or self.default_ttl)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        key = f"session:{session_id}"
        return await self.cache.get(key)
    
    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """Update session data"""
        key = f"session:{session_id}"
        success = await self.cache.set(key, data, self.default_ttl if extend_ttl else None)
        if not extend_ttl:
            # Keep existing TTL
            await self.cache.expire(key, await self.cache.get_ttl(key) or self.default_ttl)
        return success
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        key = f"session:{session_id}"
        return await self.cache.delete(key)
    
    async def extend_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Extend session TTL"""
        key = f"session:{session_id}"
        return await self.cache.expire(key, ttl or self.default_ttl)


# Global instances
cache_manager = CacheManager()
rate_limiter = RateLimiter(cache_manager)
session_manager = SessionManager(cache_manager)


# Database utility functions
async def health_check() -> Dict[str, str]:
    """Check database health"""
    try:
        # Test PostgreSQL connection
        await db.query_raw("SELECT 1")
        postgres_status = "healthy"
    except Exception as e:
        postgres_status = f"unhealthy: {str(e)}"
    
    try:
        # Test Redis connection
        async with get_redis() as redis_conn:
            if redis_conn:
                await redis_conn.ping()
                redis_status = "healthy"
            else:
                redis_status = "unhealthy: not connected"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    return {
        "postgres": postgres_status,
        "redis": redis_status
    }


async def run_migrations():
    """Run database migrations"""
    try:
        # Generate and apply Prisma migrations
        import subprocess
        result = subprocess.run(
            ["prisma", "migrate", "deploy"],
            cwd="sntry.ai",
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
            return True
        else:
            logger.error(f"Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
        return False


async def seed_database():
    """Seed database with initial data"""
    try:
        # Check if we already have data
        user_count = await db.user.count()
        if user_count > 0:
            logger.info("Database already seeded")
            return True
        
        # Create default admin user
        admin_user = await db.user.create(
            data={
                "email": "admin@sntry.ai",
                "username": "admin",
                "hashed_password": "hashed_password_here",  # Should be properly hashed
                "is_admin": True,
                "metadata": {"created_by": "system"}
            }
        )
        
        # Create system configuration
        await db.systemconfig.create(
            data={
                "key": "system_initialized",
                "value": {"timestamp": datetime.utcnow().isoformat(), "version": "1.0.0"}
            }
        )
        
        logger.info("Database seeded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        return False