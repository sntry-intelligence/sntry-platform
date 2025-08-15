from typing import Any, Dict, List, Optional
from prisma import Prisma
from prisma.models import Agent
from shared.models.base import PaginationParams
from shared.models.agent import AgentStatus, AgentConfiguration
from .base import CacheableRepository, AuditableRepository


class AgentRepository(CacheableRepository[Agent], AuditableRepository[Agent]):
    """Repository for Agent entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=600)  # 10 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> Agent:
        """Create a new agent"""
        agent = await self.db.agent.create(data=data)
        
        # Cache the new agent
        cache_key = self._get_cache_key("id", agent.id)
        await self._set_cache(cache_key, agent.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=agent.id,
            entity_type="Agent",
            new_data=agent.dict()
        )
        
        return agent
    
    async def get_by_id(self, id: str) -> Optional[Agent]:
        """Get agent by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_agent = await self._get_from_cache(cache_key)
        if cached_agent:
            return Agent(**cached_agent)
        
        # Fetch from database
        agent = await self.db.agent.find_unique(where={"id": id})
        if agent:
            await self._set_cache(cache_key, agent.dict())
        
        return agent
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Agent]:
        """Update agent by ID"""
        # Get old data for audit
        old_agent = await self.get_by_id(id)
        if not old_agent:
            return None
        
        # Update agent
        updated_agent = await self.db.agent.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="Agent",
            old_data=old_agent.dict(),
            new_data=updated_agent.dict()
        )
        
        return updated_agent
    
    async def delete(self, id: str) -> bool:
        """Delete agent by ID"""
        # Get agent for audit
        agent = await self.get_by_id(id)
        if not agent:
            return False
        
        # Delete agent (cascade will handle related records)
        await self.db.agent.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="Agent",
            old_data=agent.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[Agent], int]:
        """List agents with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get agents and total count
        agents, total = await self.db.agent.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return agents, total
    
    async def exists(self, id: str) -> bool:
        """Check if agent exists"""
        agent = await self.db.agent.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return agent is not None
    
    async def get_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        return await self.db.agent.find_first(where={"name": name})
    
    async def get_by_status(self, status: AgentStatus) -> List[Agent]:
        """Get agents by status"""
        return await self.db.agent.find_many(where={"status": status})
    
    async def get_agents_by_user(self, user_id: str) -> List[Agent]:
        """Get agents created by a specific user"""
        # This would require adding user_id to the Agent model
        # For now, we'll use metadata filtering
        return await self.db.agent.find_many(
            where={
                "metadata": {
                    "path": ["created_by"],
                    "equals": user_id
                }
            }
        )
    
    async def update_status(self, id: str, status: AgentStatus) -> Optional[Agent]:
        """Update agent status"""
        return await self.update(id, {"status": status, "updated_at": "now()"})
    
    async def update_deployment_info(
        self, 
        id: str, 
        deployment_info: Dict[str, Any]
    ) -> Optional[Agent]:
        """Update agent deployment information"""
        return await self.update(id, {
            "deployment_info": deployment_info,
            "updated_at": "now()"
        })
    
    async def search_agents(
        self,
        query: str,
        pagination: PaginationParams
    ) -> tuple[List[Agent], int]:
        """Search agents by name or description"""
        skip, take = self._calculate_pagination(pagination)
        
        where = {
            "OR": [
                {"name": {"contains": query, "mode": "insensitive"}},
                {"description": {"contains": query, "mode": "insensitive"}}
            ]
        }
        
        agents, total = await self.db.agent.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=[{"updated_at": "desc"}]
        )
        
        return agents, total
    
    async def get_agents_with_tools(self) -> List[Agent]:
        """Get agents that have tools configured"""
        return await self.db.agent.find_many(
            where={
                "tools": {
                    "some": {}
                }
            },
            include={"tools": True}
        )
    
    async def get_agents_with_workflows(self) -> List[Agent]:
        """Get agents that have workflows configured"""
        return await self.db.agent.find_many(
            where={
                "workflows": {
                    "some": {}
                }
            },
            include={"workflows": True}
        )