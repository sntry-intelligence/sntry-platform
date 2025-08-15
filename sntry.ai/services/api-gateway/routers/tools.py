from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_active_user

router = APIRouter()
settings = get_settings()


@router.post("/{agent_id}/tools")
async def register_tool(
    agent_id: str,
    tool_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Register a new tool for an agent"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.tool_management_url}/agents/{agent_id}/tools",
                json=tool_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Tool registration failed")
            )


@router.get("/{agent_id}/tools")
async def list_tools(
    agent_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """List all tools registered for an agent"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.tool_management_url}/agents/{agent_id}/tools",
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to list tools")
            )