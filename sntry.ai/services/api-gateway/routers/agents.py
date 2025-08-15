from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_user, User, Scopes, require_scopes
from shared.models.agent import (
    Agent, AgentCreateRequest, AgentUpdateRequest, 
    AgentResponse, AgentListResponse
)
from shared.models.base import PaginationParams, PaginatedResponse

router = APIRouter()
settings = get_settings()


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
@require_scopes(Scopes.AGENT_WRITE)
async def create_agent(
    request: AgentCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new AI agent"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.agent_management_url}/agents",
                json=request.dict(),
                headers={"Authorization": f"Bearer {current_user.id}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Agent creation failed")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.get("/", response_model=PaginatedResponse)
@require_scopes(Scopes.AGENT_READ)
async def list_agents(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user)
):
    """List all deployed AI agents"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.agent_management_url}/agents",
                params=pagination.dict(),
                headers={"Authorization": f"Bearer {current_user.id}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to list agents")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.get("/{agent_id}", response_model=AgentResponse)
@require_scopes(Scopes.AGENT_READ)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific AI agent"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.agent_management_url}/agents/{agent_id}",
                headers={"Authorization": f"Bearer {current_user.id}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to get agent")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.put("/{agent_id}", response_model=AgentResponse)
@require_scopes(Scopes.AGENT_WRITE)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update an existing AI agent's configuration"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{settings.agent_management_url}/agents/{agent_id}",
                json=request.dict(),
                headers={"Authorization": f"Bearer {current_user.id}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to update agent")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_scopes(Scopes.AGENT_DELETE)
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an AI agent instance"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{settings.agent_management_url}/agents/{agent_id}",
                headers={"Authorization": f"Bearer {current_user.id}"}
            )
            response.raise_for_status()
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to delete agent")
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )