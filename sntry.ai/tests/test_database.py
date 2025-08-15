"""
Unit tests for database utilities and cache management
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from shared.database import (
    CacheManager,
    RateLimiter,
    SessionManager,
    health_check,
    DatabaseManager
)


class TestCacheManager:
    """Test CacheManager class"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create CacheManager instance"""
        return CacheManager(default_ttl=300)
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager):
        """Test setting and getting cache values"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value='{"test": "value"}')
            mock_redis.setex = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test set
            result = await cache_manager.set("test_key", {"test": "value"})
            assert result is True
            mock_redis.setex.assert_called_once()
            
            # Test get
            value = await cache_manager.get("test_key")
            assert value == {"test": "value"}
            mock_redis.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, cache_manager):
        """Test deleting cache keys"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.delete = AsyncMock(return_value=1)
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test delete
            result = await cache_manager.delete("test_key")
            assert result is True
            mock_redis.delete.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_cache_delete_pattern(self, cache_manager):
        """Test deleting cache keys by pattern"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.keys = AsyncMock(return_value=["key1", "key2", "key3"])
            mock_redis.delete = AsyncMock(return_value=3)
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test delete pattern
            result = await cache_manager.delete_pattern("test_*")
            assert result == 3
            mock_redis.keys.assert_called_once_with("test_*")
            mock_redis.delete.assert_called_once_with("key1", "key2", "key3")
    
    @pytest.mark.asyncio
    async def test_cache_increment(self, cache_manager):
        """Test incrementing cache counters"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.incrby = AsyncMock(return_value=5)
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test increment
            result = await cache_manager.increment("counter_key", 2)
            assert result == 5
            mock_redis.incrby.assert_called_once_with("counter_key", 2)
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_manager):
        """Test cache error handling"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock to raise exception
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test get with error
            result = await cache_manager.get("test_key")
            assert result is None  # Should return None on error
    
    @pytest.mark.asyncio
    async def test_cache_no_redis_connection(self, cache_manager):
        """Test cache behavior when Redis is not available"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock to return None (no Redis connection)
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test operations with no Redis
            get_result = await cache_manager.get("test_key")
            set_result = await cache_manager.set("test_key", "value")
            delete_result = await cache_manager.delete("test_key")
            
            assert get_result is None
            assert set_result is False
            assert delete_result is False


class TestRateLimiter:
    """Test RateLimiter class"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create RateLimiter instance"""
        cache_manager = CacheManager()
        return RateLimiter(cache_manager)
    
    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, rate_limiter):
        """Test rate limiting when requests are allowed"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.zcard = AsyncMock(return_value=5)  # Current count
            mock_redis.zadd = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test allowed request
            allowed, info = await rate_limiter.is_allowed("test_key", 10, 60)
            
            assert allowed is True
            assert info["remaining"] == 4  # 10 - 5 - 1
            mock_redis.zadd.assert_called_once()
            mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter):
        """Test rate limiting when limit is exceeded"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.zcard = AsyncMock(return_value=10)  # At limit
            mock_redis.zrange = AsyncMock(return_value=[("1234567890", 1234567890)])
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test exceeded request
            allowed, info = await rate_limiter.is_allowed("test_key", 10, 60)
            
            assert allowed is False
            assert info["remaining"] == 0
            assert "retry_after" in info
            mock_redis.zadd.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rate_limit_no_redis(self, rate_limiter):
        """Test rate limiting when Redis is not available"""
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock to return None (no Redis connection)
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test with no Redis - should allow request
            allowed, info = await rate_limiter.is_allowed("test_key", 10, 60)
            
            assert allowed is True
            assert info["remaining"] == 10


class TestSessionManager:
    """Test SessionManager class"""
    
    @pytest.fixture
    def session_manager(self):
        """Create SessionManager instance"""
        cache_manager = CacheManager()
        return SessionManager(cache_manager, default_ttl=3600)
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test creating a session"""
        session_data = {"user_id": "user-123", "role": "admin"}
        
        # Mock cache manager
        session_manager.cache.set = AsyncMock(return_value=True)
        
        # Test create session
        result = await session_manager.create_session("session-123", session_data)
        
        assert result is True
        session_manager.cache.set.assert_called_once_with(
            "session:session-123", session_data, 3600
        )
    
    @pytest.mark.asyncio
    async def test_get_session(self, session_manager):
        """Test getting a session"""
        session_data = {"user_id": "user-123", "role": "admin"}
        
        # Mock cache manager
        session_manager.cache.get = AsyncMock(return_value=session_data)
        
        # Test get session
        result = await session_manager.get_session("session-123")
        
        assert result == session_data
        session_manager.cache.get.assert_called_once_with("session:session-123")
    
    @pytest.mark.asyncio
    async def test_update_session(self, session_manager):
        """Test updating a session"""
        session_data = {"user_id": "user-123", "role": "user"}
        
        # Mock cache manager
        session_manager.cache.set = AsyncMock(return_value=True)
        
        # Test update session
        result = await session_manager.update_session("session-123", session_data)
        
        assert result is True
        session_manager.cache.set.assert_called_once_with(
            "session:session-123", session_data, 3600
        )
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        """Test deleting a session"""
        # Mock cache manager
        session_manager.cache.delete = AsyncMock(return_value=True)
        
        # Test delete session
        result = await session_manager.delete_session("session-123")
        
        assert result is True
        session_manager.cache.delete.assert_called_once_with("session:session-123")
    
    @pytest.mark.asyncio
    async def test_extend_session(self, session_manager):
        """Test extending session TTL"""
        # Mock cache manager
        session_manager.cache.expire = AsyncMock(return_value=True)
        
        # Test extend session
        result = await session_manager.extend_session("session-123", 7200)
        
        assert result is True
        session_manager.cache.expire.assert_called_once_with("session:session-123", 7200)


class TestHealthCheck:
    """Test health check functionality"""
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """Test health check when all services are healthy"""
        with patch('shared.database.db') as mock_db, \
             patch('shared.database.get_redis') as mock_get_redis:
            
            # Setup mocks
            mock_db.query_raw = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test health check
            result = await health_check()
            
            assert result["postgres"] == "healthy"
            assert result["redis"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_postgres_unhealthy(self):
        """Test health check when PostgreSQL is unhealthy"""
        with patch('shared.database.db') as mock_db, \
             patch('shared.database.get_redis') as mock_get_redis:
            
            # Setup mocks
            mock_db.query_raw = AsyncMock(side_effect=Exception("Connection failed"))
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test health check
            result = await health_check()
            
            assert "unhealthy" in result["postgres"]
            assert result["redis"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_redis_unhealthy(self):
        """Test health check when Redis is unhealthy"""
        with patch('shared.database.db') as mock_db, \
             patch('shared.database.get_redis') as mock_get_redis:
            
            # Setup mocks
            mock_db.query_raw = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Redis down"))
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test health check
            result = await health_check()
            
            assert result["postgres"] == "healthy"
            assert "unhealthy" in result["redis"]
    
    @pytest.mark.asyncio
    async def test_health_check_redis_not_connected(self):
        """Test health check when Redis is not connected"""
        with patch('shared.database.db') as mock_db, \
             patch('shared.database.get_redis') as mock_get_redis:
            
            # Setup mocks
            mock_db.query_raw = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test health check
            result = await health_check()
            
            assert result["postgres"] == "healthy"
            assert result["redis"] == "unhealthy: not connected"


class TestDatabaseManager:
    """Test DatabaseManager class"""
    
    @pytest.mark.asyncio
    async def test_database_manager_startup(self):
        """Test DatabaseManager startup"""
        with patch('shared.database.connect_database') as mock_connect_db, \
             patch('shared.database.connect_redis') as mock_connect_redis:
            
            mock_connect_db.return_value = AsyncMock()
            mock_connect_redis.return_value = AsyncMock()
            
            manager = DatabaseManager()
            await manager.startup()
            
            mock_connect_db.assert_called_once()
            mock_connect_redis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_manager_shutdown(self):
        """Test DatabaseManager shutdown"""
        with patch('shared.database.disconnect_database') as mock_disconnect_db, \
             patch('shared.database.disconnect_redis') as mock_disconnect_redis:
            
            mock_disconnect_db.return_value = AsyncMock()
            mock_disconnect_redis.return_value = AsyncMock()
            
            manager = DatabaseManager()
            await manager.shutdown()
            
            mock_disconnect_db.assert_called_once()
            mock_disconnect_redis.assert_called_once()


class TestDatabaseIntegration:
    """Test database integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test concurrent cache operations"""
        cache_manager = CacheManager()
        
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.setex = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test concurrent operations
            tasks = []
            for i in range(10):
                task = cache_manager.set(f"key_{i}", f"value_{i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All operations should succeed
            assert all(results)
            assert mock_redis.setex.call_count == 10
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_requests(self):
        """Test rate limiter with concurrent requests"""
        cache_manager = CacheManager()
        rate_limiter = RateLimiter(cache_manager)
        
        with patch('shared.database.get_redis') as mock_get_redis:
            # Setup mock Redis
            mock_redis = AsyncMock()
            mock_redis.zremrangebyscore = AsyncMock()
            mock_redis.zcard = AsyncMock(return_value=0)  # No existing requests
            mock_redis.zadd = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_get_redis.return_value.__aenter__ = AsyncMock(return_value=mock_redis)
            mock_get_redis.return_value.__aexit__ = AsyncMock(return_value=None)
            
            # Test concurrent rate limit checks
            tasks = []
            for i in range(5):
                task = rate_limiter.is_allowed("test_key", 10, 60, f"user_{i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All requests should be allowed
            for allowed, info in results:
                assert allowed is True
    
    @pytest.mark.asyncio
    async def test_session_manager_lifecycle(self):
        """Test complete session lifecycle"""
        cache_manager = CacheManager()
        session_manager = SessionManager(cache_manager)
        
        # Mock cache operations
        cache_manager.set = AsyncMock(return_value=True)
        cache_manager.get = AsyncMock(return_value={"user_id": "user-123"})
        cache_manager.delete = AsyncMock(return_value=True)
        cache_manager.expire = AsyncMock(return_value=True)
        
        # Test session lifecycle
        session_id = "session-123"
        session_data = {"user_id": "user-123", "role": "admin"}
        
        # Create session
        create_result = await session_manager.create_session(session_id, session_data)
        assert create_result is True
        
        # Get session
        get_result = await session_manager.get_session(session_id)
        assert get_result["user_id"] == "user-123"
        
        # Update session
        updated_data = {"user_id": "user-123", "role": "user"}
        update_result = await session_manager.update_session(session_id, updated_data)
        assert update_result is True
        
        # Extend session
        extend_result = await session_manager.extend_session(session_id, 7200)
        assert extend_result is True
        
        # Delete session
        delete_result = await session_manager.delete_session(session_id)
        assert delete_result is True