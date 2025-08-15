from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_active_user

router = APIRouter()
settings = get_settings()


@router.post("/")
async def register_mcp_server(
    mcp_server_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Register a new MCP server"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.mcp_integration_url}/mcp-servers",
                json=mcp_server_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "MCP server registration failed")
            )


@router.get("/{server_id}/capabilities")
async def get_mcp_server_capabilities(
    server_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get MCP server capabilities"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.mcp_integration_url}/mcp-servers/{server_id}/capabilities",
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to get MCP server capabilities")
            )