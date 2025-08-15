from fastapi import APIRouter
from shared.database import health_check
from shared.models.base import BaseResponse

router = APIRouter()


@router.get("/", response_model=BaseResponse)
async def health_check_endpoint():
    """Health check endpoint"""
    db_health = await health_check()
    
    return BaseResponse(
        success=all(status == "healthy" for status in db_health.values()),
        message="Agent Management Service health check completed",
    )