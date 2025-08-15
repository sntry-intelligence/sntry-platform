from fastapi import APIRouter, HTTPException, status
from shared.database import get_db

router = APIRouter()


@router.post("/")
async def create_evaluation(evaluation_data: dict):
    """Create a new evaluation run"""
    # TODO: Implement evaluation creation
    return {"message": "Evaluation created", "evaluation_id": "eval_123"}


@router.get("/{run_id}")
async def get_evaluation_results(run_id: str):
    """Get evaluation results"""
    # TODO: Implement evaluation results retrieval
    return {"message": "Evaluation results", "run_id": run_id}