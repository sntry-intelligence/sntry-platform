from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_active_user

router = APIRouter()
settings = get_settings()


@router.post("/{agent_id}/conversations")
async def start_conversation(
    agent_id: str,
    conversation_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Start a new conversation with an agent"""
    # Add user ID to conversation data
    conversation_data["user_id"] = current_user.get("sub")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.agent_management_url}/agents/{agent_id}/conversations",
                json=conversation_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to start conversation")
            )


@router.post("/{agent_id}/conversations/{session_id}/messages")
async def send_message(
    agent_id: str,
    session_id: str,
    message_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Send a message to an ongoing conversation"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.agent_management_url}/agents/{agent_id}/conversations/{session_id}/messages",
                json=message_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to send message")
            )


@router.get("/{agent_id}/conversations/{session_id}")
async def get_conversation_history(
    agent_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get conversation history"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.agent_management_url}/agents/{agent_id}/conversations/{session_id}",
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to get conversation history")
            )