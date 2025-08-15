from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_active_user

router = APIRouter()
settings = get_settings()


@router.post("/{agent_id}/workflows")
async def create_workflow(
    agent_id: str,
    workflow_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new workflow for an agent"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.workflow_orchestration_url}/agents/{agent_id}/workflows",
                json=workflow_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Workflow creation failed")
            )


@router.get("/{agent_id}/workflows/{workflow_id}")
async def get_workflow(
    agent_id: str,
    workflow_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get workflow details"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.workflow_orchestration_url}/agents/{agent_id}/workflows/{workflow_id}",
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to get workflow")
            )


@router.post("/{agent_id}/workflows/{workflow_id}/execute")
async def execute_workflow(
    agent_id: str,
    workflow_id: str,
    execution_params: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Execute a workflow"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.workflow_orchestration_url}/agents/{agent_id}/workflows/{workflow_id}/execute",
                json=execution_params,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Workflow execution failed")
            )


@router.get("/{agent_id}/workflows/{workflow_id}/executions/{execution_id}")
async def get_workflow_execution(
    agent_id: str,
    workflow_id: str,
    execution_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get workflow execution status and results"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.workflow_orchestration_url}/agents/{agent_id}/workflows/{workflow_id}/executions/{execution_id}",
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to get execution status")
            )