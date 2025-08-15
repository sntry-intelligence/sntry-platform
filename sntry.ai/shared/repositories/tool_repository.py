from typing import Any, Dict, List, Optional
from prisma import Prisma
from prisma.models import Tool, ToolInvocation
from shared.models.base import PaginationParams
from shared.models.tool import ToolStatus
from .base import CacheableRepository, AuditableRepository


class ToolRepository(CacheableRepository[Tool], AuditableRepository[Tool]):
    """Repository for Tool entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=600)  # 10 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> Tool:
        """Create a new tool"""
        tool = await self.db.tool.create(data=data)
        
        # Cache the new tool
        cache_key = self._get_cache_key("id", tool.id)
        await self._set_cache(cache_key, tool.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=tool.id,
            entity_type="Tool",
            new_data=tool.dict()
        )
        
        return tool
    
    async def get_by_id(self, id: str) -> Optional[Tool]:
        """Get tool by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_tool = await self._get_from_cache(cache_key)
        if cached_tool:
            return Tool(**cached_tool)
        
        # Fetch from database
        tool = await self.db.tool.find_unique(where={"id": id})
        if tool:
            await self._set_cache(cache_key, tool.dict())
        
        return tool
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Tool]:
        """Update tool by ID"""
        # Get old data for audit
        old_tool = await self.get_by_id(id)
        if not old_tool:
            return None
        
        # Update tool
        updated_tool = await self.db.tool.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="Tool",
            old_data=old_tool.dict(),
            new_data=updated_tool.dict()
        )
        
        return updated_tool
    
    async def delete(self, id: str) -> bool:
        """Delete tool by ID"""
        # Get tool for audit
        tool = await self.get_by_id(id)
        if not tool:
            return False
        
        # Delete tool (cascade will handle invocations)
        await self.db.tool.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="Tool",
            old_data=tool.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[Tool], int]:
        """List tools with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get tools and total count
        tools, total = await self.db.tool.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return tools, total
    
    async def exists(self, id: str) -> bool:
        """Check if tool exists"""
        tool = await self.db.tool.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return tool is not None
    
    async def get_by_agent_id(self, agent_id: str) -> List[Tool]:
        """Get tools by agent ID"""
        return await self.db.tool.find_many(where={"agent_id": agent_id})
    
    async def get_by_name(self, agent_id: str, name: str) -> Optional[Tool]:
        """Get tool by agent ID and name"""
        return await self.db.tool.find_first(
            where={
                "agent_id": agent_id,
                "name": name
            }
        )
    
    async def get_by_status(self, status: ToolStatus) -> List[Tool]:
        """Get tools by status"""
        return await self.db.tool.find_many(where={"status": status})
    
    async def get_by_mcp_server(self, mcp_server_id: str) -> List[Tool]:
        """Get tools by MCP server ID"""
        return await self.db.tool.find_many(where={"mcp_server_id": mcp_server_id})
    
    async def update_status(self, id: str, status: ToolStatus) -> Optional[Tool]:
        """Update tool status"""
        return await self.update(id, {"status": status, "updated_at": "now()"})
    
    async def search_tools(
        self,
        query: str,
        agent_id: Optional[str] = None,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Tool], int]:
        """Search tools by name or description"""
        where = {
            "OR": [
                {"name": {"contains": query, "mode": "insensitive"}},
                {"description": {"contains": query, "mode": "insensitive"}}
            ]
        }
        
        if agent_id:
            where["agent_id"] = agent_id
        
        if pagination:
            skip, take = self._calculate_pagination(pagination)
            tools, total = await self.db.tool.find_many_and_count(
                where=where,
                skip=skip,
                take=take,
                order=[{"updated_at": "desc"}]
            )
        else:
            tools = await self.db.tool.find_many(
                where=where,
                order=[{"updated_at": "desc"}]
            )
            total = len(tools)
        
        return tools, total
    
    async def get_tools_with_invocations(self, agent_id: str) -> List[Tool]:
        """Get tools with their invocation history"""
        return await self.db.tool.find_many(
            where={"agent_id": agent_id},
            include={"invocations": {"take": 10, "order_by": {"created_at": "desc"}}}
        )


class ToolInvocationRepository(CacheableRepository[ToolInvocation], AuditableRepository[ToolInvocation]):
    """Repository for ToolInvocation entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=300)  # 5 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> ToolInvocation:
        """Create a new tool invocation"""
        invocation = await self.db.toolinvocation.create(data=data)
        
        # Cache the new invocation
        cache_key = self._get_cache_key("id", invocation.id)
        await self._set_cache(cache_key, invocation.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=invocation.id,
            entity_type="ToolInvocation",
            new_data=invocation.dict()
        )
        
        return invocation
    
    async def get_by_id(self, id: str) -> Optional[ToolInvocation]:
        """Get tool invocation by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_invocation = await self._get_from_cache(cache_key)
        if cached_invocation:
            return ToolInvocation(**cached_invocation)
        
        # Fetch from database
        invocation = await self.db.toolinvocation.find_unique(where={"id": id})
        if invocation:
            await self._set_cache(cache_key, invocation.dict())
        
        return invocation
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[ToolInvocation]:
        """Update tool invocation by ID"""
        # Get old data for audit
        old_invocation = await self.get_by_id(id)
        if not old_invocation:
            return None
        
        # Update invocation
        updated_invocation = await self.db.toolinvocation.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="ToolInvocation",
            old_data=old_invocation.dict(),
            new_data=updated_invocation.dict()
        )
        
        return updated_invocation
    
    async def delete(self, id: str) -> bool:
        """Delete tool invocation by ID"""
        # Get invocation for audit
        invocation = await self.get_by_id(id)
        if not invocation:
            return False
        
        # Delete invocation
        await self.db.toolinvocation.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="ToolInvocation",
            old_data=invocation.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[ToolInvocation], int]:
        """List tool invocations with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get invocations and total count
        invocations, total = await self.db.toolinvocation.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return invocations, total
    
    async def exists(self, id: str) -> bool:
        """Check if tool invocation exists"""
        invocation = await self.db.toolinvocation.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return invocation is not None
    
    async def get_by_tool_id(self, tool_id: str) -> List[ToolInvocation]:
        """Get invocations by tool ID"""
        return await self.db.toolinvocation.find_many(
            where={"tool_id": tool_id},
            order=[{"created_at": "desc"}]
        )
    
    async def get_by_status(self, status: str) -> List[ToolInvocation]:
        """Get invocations by status"""
        return await self.db.toolinvocation.find_many(where={"status": status})
    
    async def update_status(self, id: str, status: str) -> Optional[ToolInvocation]:
        """Update invocation status"""
        return await self.update(id, {"status": status})
    
    async def complete_invocation(
        self,
        id: str,
        result: Dict[str, Any],
        status: str = "completed",
        duration: Optional[int] = None
    ) -> Optional[ToolInvocation]:
        """Complete tool invocation"""
        update_data = {
            "result": result,
            "status": status,
            "completed_at": "now()"
        }
        
        if duration is not None:
            update_data["duration"] = duration
        
        return await self.update(id, update_data)
    
    async def get_invocation_stats(self, tool_id: str) -> Dict[str, Any]:
        """Get invocation statistics for a tool"""
        # Get total invocations
        total = await self.db.toolinvocation.count(where={"tool_id": tool_id})
        
        # Get successful invocations
        successful = await self.db.toolinvocation.count(
            where={"tool_id": tool_id, "status": "completed"}
        )
        
        # Get failed invocations
        failed = await self.db.toolinvocation.count(
            where={"tool_id": tool_id, "status": "failed"}
        )
        
        # Get average duration
        avg_duration_result = await self.db.query_raw(
            "SELECT AVG(duration) as avg_duration FROM tool_invocations WHERE tool_id = $1 AND duration IS NOT NULL",
            tool_id
        )
        avg_duration = avg_duration_result[0]["avg_duration"] if avg_duration_result else 0
        
        return {
            "total_invocations": total,
            "successful_invocations": successful,
            "failed_invocations": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "average_duration_ms": float(avg_duration) if avg_duration else 0
        }
    
    async def get_recent_invocations(
        self,
        tool_id: str,
        limit: int = 10
    ) -> List[ToolInvocation]:
        """Get recent invocations for a tool"""
        return await self.db.toolinvocation.find_many(
            where={"tool_id": tool_id},
            order=[{"created_at": "desc"}],
            take=limit
        )