from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_active_user

router = APIRouter()
settings = get_settings()


@router.post("/")
async def create_evaluation(
    evaluation_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new evaluation run"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.agent_management_url}/evaluations",
                json=evaluation_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Evaluation creation failed")
            )


@router.get("/{run_id}")
async def get_evaluation_results(
    run_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get evaluation results"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.agent_management_url}/evaluations/{run_id}",
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Failed to get evaluation results")
            )