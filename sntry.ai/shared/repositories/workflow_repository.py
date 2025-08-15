from typing import Any, Dict, List, Optional
from prisma import Prisma
from prisma.models import Workflow, WorkflowExecution
from shared.models.base import PaginationParams
from shared.models.workflow import WorkflowStatus, ExecutionStatus
from .base import CacheableRepository, AuditableRepository


class WorkflowRepository(CacheableRepository[Workflow], AuditableRepository[Workflow]):
    """Repository for Workflow entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=300)  # 5 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> Workflow:
        """Create a new workflow"""
        workflow = await self.db.workflow.create(data=data)
        
        # Cache the new workflow
        cache_key = self._get_cache_key("id", workflow.id)
        await self._set_cache(cache_key, workflow.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=workflow.id,
            entity_type="Workflow",
            new_data=workflow.dict()
        )
        
        return workflow
    
    async def get_by_id(self, id: str) -> Optional[Workflow]:
        """Get workflow by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_workflow = await self._get_from_cache(cache_key)
        if cached_workflow:
            return Workflow(**cached_workflow)
        
        # Fetch from database
        workflow = await self.db.workflow.find_unique(where={"id": id})
        if workflow:
            await self._set_cache(cache_key, workflow.dict())
        
        return workflow
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Workflow]:
        """Update workflow by ID"""
        # Get old data for audit
        old_workflow = await self.get_by_id(id)
        if not old_workflow:
            return None
        
        # Update workflow
        updated_workflow = await self.db.workflow.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="Workflow",
            old_data=old_workflow.dict(),
            new_data=updated_workflow.dict()
        )
        
        return updated_workflow
    
    async def delete(self, id: str) -> bool:
        """Delete workflow by ID"""
        # Get workflow for audit
        workflow = await self.get_by_id(id)
        if not workflow:
            return False
        
        # Delete workflow (cascade will handle executions)
        await self.db.workflow.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="Workflow",
            old_data=workflow.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[Workflow], int]:
        """List workflows with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get workflows and total count
        workflows, total = await self.db.workflow.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return workflows, total
    
    async def exists(self, id: str) -> bool:
        """Check if workflow exists"""
        workflow = await self.db.workflow.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return workflow is not None
    
    async def get_by_agent_id(self, agent_id: str) -> List[Workflow]:
        """Get workflows by agent ID"""
        return await self.db.workflow.find_many(where={"agent_id": agent_id})
    
    async def get_by_status(self, status: WorkflowStatus) -> List[Workflow]:
        """Get workflows by status"""
        return await self.db.workflow.find_many(where={"status": status})
    
    async def update_status(self, id: str, status: WorkflowStatus) -> Optional[Workflow]:
        """Update workflow status"""
        return await self.update(id, {"status": status, "updated_at": "now()"})
    
    async def get_with_executions(self, id: str) -> Optional[Workflow]:
        """Get workflow with its executions"""
        return await self.db.workflow.find_unique(
            where={"id": id},
            include={"executions": True}
        )


class WorkflowExecutionRepository(CacheableRepository[WorkflowExecution], AuditableRepository[WorkflowExecution]):
    """Repository for WorkflowExecution entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=180)  # 3 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> WorkflowExecution:
        """Create a new workflow execution"""
        execution = await self.db.workflowexecution.create(data=data)
        
        # Cache the new execution
        cache_key = self._get_cache_key("id", execution.id)
        await self._set_cache(cache_key, execution.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=execution.id,
            entity_type="WorkflowExecution",
            new_data=execution.dict()
        )
        
        return execution
    
    async def get_by_id(self, id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_execution = await self._get_from_cache(cache_key)
        if cached_execution:
            return WorkflowExecution(**cached_execution)
        
        # Fetch from database
        execution = await self.db.workflowexecution.find_unique(where={"id": id})
        if execution:
            await self._set_cache(cache_key, execution.dict())
        
        return execution
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[WorkflowExecution]:
        """Update workflow execution by ID"""
        # Get old data for audit
        old_execution = await self.get_by_id(id)
        if not old_execution:
            return None
        
        # Update execution
        updated_execution = await self.db.workflowexecution.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="WorkflowExecution",
            old_data=old_execution.dict(),
            new_data=updated_execution.dict()
        )
        
        return updated_execution
    
    async def delete(self, id: str) -> bool:
        """Delete workflow execution by ID"""
        # Get execution for audit
        execution = await self.get_by_id(id)
        if not execution:
            return False
        
        # Delete execution
        await self.db.workflowexecution.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="WorkflowExecution",
            old_data=execution.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[WorkflowExecution], int]:
        """List workflow executions with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get executions and total count
        executions, total = await self.db.workflowexecution.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return executions, total
    
    async def exists(self, id: str) -> bool:
        """Check if workflow execution exists"""
        execution = await self.db.workflowexecution.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return execution is not None
    
    async def get_by_workflow_id(self, workflow_id: str) -> List[WorkflowExecution]:
        """Get executions by workflow ID"""
        return await self.db.workflowexecution.find_many(
            where={"workflow_id": workflow_id},
            order=[{"created_at": "desc"}]
        )
    
    async def get_by_status(self, status: ExecutionStatus) -> List[WorkflowExecution]:
        """Get executions by status"""
        return await self.db.workflowexecution.find_many(where={"status": status})
    
    async def update_status(self, id: str, status: ExecutionStatus) -> Optional[WorkflowExecution]:
        """Update execution status"""
        return await self.update(id, {"status": status, "updated_at": "now()"})
    
    async def update_progress(
        self, 
        id: str, 
        current_step: int, 
        results: Dict[str, Any]
    ) -> Optional[WorkflowExecution]:
        """Update execution progress"""
        return await self.update(id, {
            "current_step": current_step,
            "results": results,
            "updated_at": "now()"
        })
    
    async def complete_execution(
        self, 
        id: str, 
        results: Dict[str, Any],
        status: ExecutionStatus = ExecutionStatus.COMPLETED
    ) -> Optional[WorkflowExecution]:
        """Complete workflow execution"""
        return await self.update(id, {
            "status": status,
            "results": results,
            "end_time": "now()",
            "updated_at": "now()"
        })
    
    async def get_running_executions(self) -> List[WorkflowExecution]:
        """Get all running executions"""
        return await self.db.workflowexecution.find_many(
            where={"status": ExecutionStatus.RUNNING}
        )
    
    async def get_executions_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[WorkflowExecution]:
        """Get executions within date range"""
        return await self.db.workflowexecution.find_many(
            where={
                "created_at": {
                    "gte": start_date,
                    "lte": end_date
                }
            },
            order=[{"created_at": "desc"}]
        )