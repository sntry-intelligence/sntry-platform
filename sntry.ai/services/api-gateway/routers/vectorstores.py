from fastapi import APIRouter, HTTPException, Depends, status
import httpx

from shared.config import get_settings
from shared.auth import get_current_active_user

router = APIRouter()
settings = get_settings()


@router.post("/")
async def create_vector_store(
    vector_store_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a new vector store"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.vector_database_url}/vectorstores",
                json=vector_store_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Vector store creation failed")
            )


@router.post("/{store_id}/embeddings")
async def ingest_embeddings(
    store_id: str,
    ingestion_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Ingest data into vector store"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.vector_database_url}/vectorstores/{store_id}/embeddings",
                json=ingestion_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Embedding ingestion failed")
            )


@router.post("/{store_id}/query")
async def query_vector_store(
    store_id: str,
    query_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Query vector store for similar documents"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.vector_database_url}/vectorstores/{store_id}/query",
                json=query_data,
                headers={"Authorization": f"Bearer {current_user.get('token')}"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.json().get("detail", "Vector query failed")
            )