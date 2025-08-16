"""
Background Task Management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from app.core.database import get_postgres_db

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory task storage for demo purposes
# In production, this would be stored in Redis or a database
task_storage: Dict[str, Dict[str, Any]] = {}


class TaskManager:
    """Simple task manager for tracking background tasks"""
    
    @staticmethod
    def create_task(task_type: str, parameters: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """Create a new task and return task ID"""
        task_id = str(uuid.uuid4())
        
        task_storage[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "pending",
            "parameters": parameters,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "progress": 0,
            "result": None,
            "error": None,
            "logs": []
        }
        
        logger.info(f"Created task {task_id} of type {task_type}")
        return task_id
    
    @staticmethod
    def get_task(task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        return task_storage.get(task_id)
    
    @staticmethod
    def update_task_status(task_id: str, status: str, progress: int = None, result: Any = None, error: str = None):
        """Update task status"""
        if task_id in task_storage:
            task = task_storage[task_id]
            task["status"] = status
            
            if progress is not None:
                task["progress"] = progress
            
            if result is not None:
                task["result"] = result
            
            if error is not None:
                task["error"] = error
            
            if status == "running" and task["started_at"] is None:
                task["started_at"] = datetime.utcnow()
            elif status in ["completed", "failed"]:
                task["completed_at"] = datetime.utcnow()
            
            logger.info(f"Updated task {task_id} status to {status}")
    
    @staticmethod
    def add_task_log(task_id: str, message: str, level: str = "info"):
        """Add log entry to task"""
        if task_id in task_storage:
            task_storage[task_id]["logs"].append({
                "timestamp": datetime.utcnow(),
                "level": level,
                "message": message
            })
    
    @staticmethod
    def get_all_tasks(task_type: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks with optional filtering"""
        tasks = list(task_storage.values())
        
        if task_type:
            tasks = [t for t in tasks if t["task_type"] == task_type]
        
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        
        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)


def get_task_manager() -> TaskManager:
    """Dependency to get task manager"""
    return TaskManager()


@router.get("/health")
async def tasks_health():
    """Task management health check"""
    return {"status": "healthy", "module": "task_management"}


@router.post("/tasks/scrape", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scraping_job(
    source: str = Query(..., description="Scraping source (findyello, workandjam, all)"),
    category: Optional[str] = Query(None, description="Specific category to scrape"),
    location: Optional[str] = Query(None, description="Specific location to scrape"),
    full_scrape: bool = Query(False, description="Perform full scrape instead of incremental"),
    max_pages: Optional[int] = Query(None, description="Maximum pages to scrape"),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Trigger scraping job with task ID response"""
    try:
        # Validate source
        valid_sources = ["findyello", "workandjam", "all"]
        if source not in valid_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
            )
        
        # Create task parameters
        parameters = {
            "source": source,
            "category": category,
            "location": location,
            "full_scrape": full_scrape,
            "max_pages": max_pages
        }
        
        # Create task
        task_id = task_manager.create_task("scraping", parameters)
        
        # In a real implementation, this would trigger a Celery task
        # For now, we'll simulate the task creation
        task_manager.add_task_log(task_id, f"Scraping task created for source: {source}")
        
        # Simulate task progression (in real implementation, Celery would handle this)
        import asyncio
        asyncio.create_task(_simulate_scraping_task(task_id, parameters, task_manager))
        
        return {
            "task_id": task_id,
            "status": "accepted",
            "message": f"Scraping task created for {source}",
            "parameters": parameters,
            "estimated_duration_minutes": _estimate_scraping_duration(parameters)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scraping task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scraping task"
        )


@router.post("/tasks/geocode_batch", status_code=status.HTTP_202_ACCEPTED)
async def trigger_batch_geocoding(
    business_ids: Optional[str] = Query(None, description="Comma-separated business IDs to geocode"),
    category: Optional[str] = Query(None, description="Geocode businesses in specific category"),
    limit: int = Query(100, description="Maximum number of businesses to geocode"),
    retry_failed: bool = Query(False, description="Retry previously failed geocoding attempts"),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Trigger batch geocoding operations"""
    try:
        # Parse business IDs if provided
        parsed_business_ids = None
        if business_ids:
            try:
                parsed_business_ids = [int(id.strip()) for id in business_ids.split(",")]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid business IDs format"
                )
        
        # Create task parameters
        parameters = {
            "business_ids": parsed_business_ids,
            "category": category,
            "limit": limit,
            "retry_failed": retry_failed
        }
        
        # Create task
        task_id = task_manager.create_task("batch_geocoding", parameters)
        
        task_manager.add_task_log(task_id, f"Batch geocoding task created for {limit} businesses")
        
        # Simulate task progression
        import asyncio
        asyncio.create_task(_simulate_geocoding_task(task_id, parameters, task_manager))
        
        return {
            "task_id": task_id,
            "status": "accepted",
            "message": f"Batch geocoding task created",
            "parameters": parameters,
            "estimated_duration_minutes": _estimate_geocoding_duration(parameters)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating batch geocoding task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create batch geocoding task"
        )


@router.post("/tasks/customer-sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_customer_sync(
    source_system: str = Query(..., description="Source system (quickbooks, sheets, manual)"),
    sync_type: str = Query("incremental", description="Sync type (full, incremental)"),
    customer_ids: Optional[str] = Query(None, description="Specific customer IDs to sync"),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Trigger legacy system integration for customer data sync"""
    try:
        # Validate source system
        valid_sources = ["quickbooks", "sheets", "manual", "all"]
        if source_system not in valid_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source system. Must be one of: {', '.join(valid_sources)}"
            )
        
        # Validate sync type
        valid_sync_types = ["full", "incremental"]
        if sync_type not in valid_sync_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sync type. Must be one of: {', '.join(valid_sync_types)}"
            )
        
        # Parse customer IDs if provided
        parsed_customer_ids = None
        if customer_ids:
            try:
                parsed_customer_ids = [int(id.strip()) for id in customer_ids.split(",")]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid customer IDs format"
                )
        
        # Create task parameters
        parameters = {
            "source_system": source_system,
            "sync_type": sync_type,
            "customer_ids": parsed_customer_ids
        }
        
        # Create task
        task_id = task_manager.create_task("customer_sync", parameters)
        
        task_manager.add_task_log(task_id, f"Customer sync task created for {source_system}")
        
        # Simulate task progression
        import asyncio
        asyncio.create_task(_simulate_customer_sync_task(task_id, parameters, task_manager))
        
        return {
            "task_id": task_id,
            "status": "accepted",
            "message": f"Customer sync task created for {source_system}",
            "parameters": parameters,
            "estimated_duration_minutes": _estimate_sync_duration(parameters)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer sync task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create customer sync task"
        )


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Get task status and details by task ID"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Calculate duration if task is completed
        duration_seconds = None
        if task["completed_at"] and task["started_at"]:
            duration_seconds = (task["completed_at"] - task["started_at"]).total_seconds()
        
        return {
            "task_id": task["task_id"],
            "task_type": task["task_type"],
            "status": task["status"],
            "progress": task["progress"],
            "parameters": task["parameters"],
            "created_at": task["created_at"],
            "started_at": task["started_at"],
            "completed_at": task["completed_at"],
            "duration_seconds": duration_seconds,
            "result": task["result"],
            "error": task["error"],
            "logs": task["logs"][-10:]  # Return last 10 log entries
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status"
        )


@router.get("/tasks")
async def get_all_tasks(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of tasks to return"),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Get all tasks with optional filtering"""
    try:
        tasks = task_manager.get_all_tasks(task_type, status)
        
        # Limit results
        tasks = tasks[:limit]
        
        # Format response
        formatted_tasks = []
        for task in tasks:
            duration_seconds = None
            if task["completed_at"] and task["started_at"]:
                duration_seconds = (task["completed_at"] - task["started_at"]).total_seconds()
            
            formatted_tasks.append({
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "status": task["status"],
                "progress": task["progress"],
                "created_at": task["created_at"],
                "started_at": task["started_at"],
                "completed_at": task["completed_at"],
                "duration_seconds": duration_seconds,
                "has_error": task["error"] is not None,
                "log_count": len(task["logs"])
            })
        
        return {
            "tasks": formatted_tasks,
            "total": len(formatted_tasks),
            "filters": {
                "task_type": task_type,
                "status": status
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks"
        )


@router.get("/tasks/{task_id}/result")
async def get_task_result(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Get task result data"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        if task["status"] not in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task is not completed. Current status: {task['status']}"
            )
        
        return {
            "task_id": task_id,
            "status": task["status"],
            "result": task["result"],
            "error": task["error"],
            "completed_at": task["completed_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task result {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task result"
        )


@router.get("/tasks/{task_id}/logs")
async def get_task_logs(
    task_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries"),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Get task execution logs"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        logs = task["logs"][-limit:]  # Get last N log entries
        
        return {
            "task_id": task_id,
            "logs": logs,
            "total_logs": len(task["logs"]),
            "showing_last": len(logs)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task logs {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task logs"
        )


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
):
    """Cancel a running task"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        if task["status"] in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel task with status: {task['status']}"
            )
        
        # Update task status to cancelled
        task_manager.update_task_status(task_id, "cancelled")
        task_manager.add_task_log(task_id, "Task cancelled by user request", "warning")
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task has been cancelled"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task"
        )


# Helper functions for task simulation and estimation

def _estimate_scraping_duration(parameters: Dict[str, Any]) -> int:
    """Estimate scraping duration in minutes"""
    base_duration = 5  # Base 5 minutes
    
    if parameters.get("full_scrape"):
        base_duration *= 3
    
    if parameters.get("source") == "all":
        base_duration *= 2
    
    max_pages = parameters.get("max_pages", 10)
    base_duration += max_pages * 0.5
    
    return int(base_duration)


def _estimate_geocoding_duration(parameters: Dict[str, Any]) -> int:
    """Estimate geocoding duration in minutes"""
    limit = parameters.get("limit", 100)
    # Assume 1 second per geocoding request
    return max(1, int(limit / 60))


def _estimate_sync_duration(parameters: Dict[str, Any]) -> int:
    """Estimate sync duration in minutes"""
    base_duration = 2
    
    if parameters.get("sync_type") == "full":
        base_duration *= 5
    
    if parameters.get("source_system") == "all":
        base_duration *= 3
    
    return base_duration


# Simulation functions (in production, these would be Celery tasks)

async def _simulate_scraping_task(task_id: str, parameters: Dict[str, Any], task_manager: TaskManager):
    """Simulate scraping task execution"""
    import asyncio
    
    try:
        task_manager.update_task_status(task_id, "running", 0)
        task_manager.add_task_log(task_id, "Starting scraping task")
        
        # Simulate progress
        for progress in [10, 25, 50, 75, 90]:
            await asyncio.sleep(2)  # Simulate work
            task_manager.update_task_status(task_id, "running", progress)
            task_manager.add_task_log(task_id, f"Scraping progress: {progress}%")
        
        # Simulate completion
        await asyncio.sleep(1)
        result = {
            "businesses_scraped": 150,
            "new_businesses": 45,
            "updated_businesses": 105,
            "errors": 2,
            "source": parameters.get("source")
        }
        
        task_manager.update_task_status(task_id, "completed", 100, result)
        task_manager.add_task_log(task_id, "Scraping task completed successfully")
        
    except Exception as e:
        task_manager.update_task_status(task_id, "failed", error=str(e))
        task_manager.add_task_log(task_id, f"Scraping task failed: {e}", "error")


async def _simulate_geocoding_task(task_id: str, parameters: Dict[str, Any], task_manager: TaskManager):
    """Simulate geocoding task execution"""
    import asyncio
    
    try:
        task_manager.update_task_status(task_id, "running", 0)
        task_manager.add_task_log(task_id, "Starting batch geocoding")
        
        # Simulate progress
        for progress in [20, 40, 60, 80, 100]:
            await asyncio.sleep(1)
            task_manager.update_task_status(task_id, "running", progress)
            task_manager.add_task_log(task_id, f"Geocoding progress: {progress}%")
        
        # Simulate completion
        result = {
            "businesses_processed": parameters.get("limit", 100),
            "successful_geocodes": 85,
            "failed_geocodes": 15,
            "api_calls_used": 85
        }
        
        task_manager.update_task_status(task_id, "completed", 100, result)
        task_manager.add_task_log(task_id, "Batch geocoding completed")
        
    except Exception as e:
        task_manager.update_task_status(task_id, "failed", error=str(e))
        task_manager.add_task_log(task_id, f"Geocoding task failed: {e}", "error")


async def _simulate_customer_sync_task(task_id: str, parameters: Dict[str, Any], task_manager: TaskManager):
    """Simulate customer sync task execution"""
    import asyncio
    
    try:
        task_manager.update_task_status(task_id, "running", 0)
        task_manager.add_task_log(task_id, f"Starting customer sync from {parameters.get('source_system')}")
        
        # Simulate progress
        for progress in [15, 35, 55, 75, 95]:
            await asyncio.sleep(1.5)
            task_manager.update_task_status(task_id, "running", progress)
            task_manager.add_task_log(task_id, f"Sync progress: {progress}%")
        
        # Simulate completion
        result = {
            "customers_processed": 200,
            "new_customers": 25,
            "updated_customers": 175,
            "sync_errors": 3,
            "source_system": parameters.get("source_system")
        }
        
        task_manager.update_task_status(task_id, "completed", 100, result)
        task_manager.add_task_log(task_id, "Customer sync completed successfully")
        
    except Exception as e:
        task_manager.update_task_status(task_id, "failed", error=str(e))
        task_manager.add_task_log(task_id, f"Customer sync failed: {e}", "error")