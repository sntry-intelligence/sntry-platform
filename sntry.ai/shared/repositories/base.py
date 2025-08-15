from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from datetime import datetime
from prisma import Prisma
from shared.models.base import PaginationParams

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Base repository class with common CRUD operations"""
    
    def __init__(self, db: Prisma):
        self.db = db
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new record"""
        pass
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get a record by ID"""
        pass
    
    @abstractmethod
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a record by ID"""
        pass
    
    @abstractmethod
    async def list(
        self, 
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[T], int]:
        """List records with pagination and filtering"""
        pass
    
    @abstractmethod
    async def exists(self, id: str) -> bool:
        """Check if a record exists"""
        pass
    
    def _build_where_clause(self, filters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build where clause from filters"""
        if not filters:
            return {}
        
        where = {}
        for key, value in filters.items():
            if isinstance(value, dict):
                # Handle complex filters like {"status": {"in": ["ACTIVE", "PENDING"]}}
                where[key] = value
            elif isinstance(value, list):
                # Handle list filters as "in" operations
                where[key] = {"in": value}
            else:
                # Simple equality filter
                where[key] = value
        
        return where
    
    def _build_order_by(self, order_by: Optional[Dict[str, str]]) -> List[Dict[str, str]]:
        """Build order by clause"""
        if not order_by:
            return [{"created_at": "desc"}]  # Default ordering
        
        order_list = []
        for field, direction in order_by.items():
            order_list.append({field: direction.lower()})
        
        return order_list
    
    def _calculate_pagination(self, pagination: PaginationParams) -> tuple[int, int]:
        """Calculate skip and take values for pagination"""
        skip = (pagination.page - 1) * pagination.size
        take = pagination.size
        return skip, take


class CacheableRepository(BaseRepository[T]):
    """Repository with caching capabilities"""
    
    def __init__(self, db: Prisma, cache_ttl: int = 300):
        super().__init__(db)
        self.cache_ttl = cache_ttl  # Cache TTL in seconds
    
    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key"""
        return f"{self.__class__.__name__.lower()}:{prefix}:{identifier}"
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            from shared.database import get_redis
            async with get_redis() as redis:
                if redis:
                    cached_data = await redis.get(key)
                    if cached_data:
                        import json
                        return json.loads(cached_data)
        except Exception:
            # Cache miss or error, continue without cache
            pass
        return None
    
    async def _set_cache(self, key: str, value: Any) -> None:
        """Set value in cache"""
        try:
            from shared.database import get_redis
            async with get_redis() as redis:
                if redis:
                    import json
                    await redis.setex(key, self.cache_ttl, json.dumps(value, default=str))
        except Exception:
            # Cache error, continue without cache
            pass
    
    async def _delete_cache(self, pattern: str) -> None:
        """Delete cache entries matching pattern"""
        try:
            from shared.database import get_redis
            async with get_redis() as redis:
                if redis:
                    keys = await redis.keys(pattern)
                    if keys:
                        await redis.delete(*keys)
        except Exception:
            # Cache error, continue without cache
            pass
    
    async def invalidate_cache(self, id: str) -> None:
        """Invalidate cache for a specific record"""
        cache_pattern = f"{self.__class__.__name__.lower()}:*:{id}*"
        await self._delete_cache(cache_pattern)


class AuditableRepository(BaseRepository[T]):
    """Repository with audit trail capabilities"""
    
    async def _create_audit_log(
        self, 
        action: str, 
        entity_id: str, 
        entity_type: str,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Create audit log entry"""
        try:
            audit_data = {
                "action": action,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "old_data": old_data,
                "new_data": new_data,
                "user_id": user_id,
                "timestamp": datetime.utcnow(),
                "ip_address": None,  # Could be passed from request context
                "user_agent": None   # Could be passed from request context
            }
            
            # Store audit log (could be in separate audit table or external system)
            # For now, we'll use logging
            import logging
            logger = logging.getLogger("audit")
            logger.info(f"Audit: {audit_data}")
            
        except Exception as e:
            # Audit logging should not break the main operation
            import logging
            logger = logging.getLogger("audit")
            logger.error(f"Failed to create audit log: {e}")


class TransactionalRepository(BaseRepository[T]):
    """Repository with transaction support"""
    
    async def execute_in_transaction(self, operations: List[callable]) -> List[Any]:
        """Execute multiple operations in a transaction"""
        async with self.db.tx() as transaction:
            results = []
            for operation in operations:
                result = await operation(transaction)
                results.append(result)
            return results
    
    async def create_with_relations(
        self, 
        main_data: Dict[str, Any], 
        related_operations: List[callable]
    ) -> T:
        """Create main entity with related entities in a transaction"""
        async with self.db.tx() as transaction:
            # Create main entity
            main_entity = await self._create_main_entity(transaction, main_data)
            
            # Execute related operations
            for operation in related_operations:
                await operation(transaction, main_entity.id)
            
            return main_entity
    
    @abstractmethod
    async def _create_main_entity(self, transaction: Prisma, data: Dict[str, Any]) -> T:
        """Create main entity within transaction"""
        pass