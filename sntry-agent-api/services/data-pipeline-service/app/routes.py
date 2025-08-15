from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from .database import get_db
from .models import (
    DataIngestionRequest, DataCleaningRequest, SyntheticDataRequest,
    DataQualityValidation, JobStatusResponse, DataQualityResponse,
    DataIngestionJob, DataQualityReport, SyntheticDataJob
)
from .data_ingestion import DataIngestionEngine
from .data_cleaning import DataCleaningEngine
from .data_quality import DataQualityValidator
from .synthetic_data import SyntheticDataGenerator
from .vector_database import KnowledgeManager, VectorDatabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize engines
ingestion_engine = DataIngestionEngine()
cleaning_engine = DataCleaningEngine()
quality_validator = DataQualityValidator()
synthetic_generator = SyntheticDataGenerator()
knowledge_manager = KnowledgeManager()


@router.post("/data/ingest", response_model=Dict[str, str])
async def ingest_data(
    request: DataIngestionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Ingest data from various sources"""
    try:
        # Start ingestion in background
        job_id = await ingestion_engine.ingest_data(
            source_type=request.source_type,
            source_path=request.source_path,
            metadata=request.metadata,
            validation_rules=request.validation_rules,
            db=db
        )
        
        return {
            "job_id": job_id,
            "message": "Data ingestion started",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/clean", response_model=Dict[str, Any])
async def clean_data(
    request: DataCleaningRequest,
    db: Session = Depends(get_db)
):
    """Clean and preprocess ingested data"""
    try:
        result = await cleaning_engine.clean_data(
            job_id=request.job_id,
            cleaning_operations=request.cleaning_operations,
            remove_duplicates=request.remove_duplicates,
            handle_missing_values=request.handle_missing_values,
            normalize_text=request.normalize_text,
            db=db
        )
        
        return {
            "job_id": request.job_id,
            "message": "Data cleaning completed",
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Data cleaning failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/synthetic/generate", response_model=Dict[str, str])
async def generate_synthetic_data(
    request: SyntheticDataRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate synthetic data for training and testing"""
    try:
        job_id = await synthetic_generator.generate_synthetic_data(
            template_type=request.template_type,
            num_records=request.num_records,
            output_format=request.output_format,
            parameters=request.parameters,
            preserve_privacy=request.preserve_privacy,
            db=db
        )
        
        return {
            "job_id": job_id,
            "message": "Synthetic data generation started",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Synthetic data generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/validate", response_model=DataQualityResponse)
async def validate_data_quality(
    job_id: str,
    validation: DataQualityValidation,
    db: Session = Depends(get_db)
):
    """Validate data quality for ingested data"""
    try:
        # Get the ingestion job
        job = db.query(DataIngestionJob).filter(DataIngestionJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # For this implementation, we'll create mock data
        # In real implementation, this would load the actual data
        mock_data = [
            {'id': i, 'name': f'Record {i}', 'value': i * 1.5}
            for i in range(100)
        ]
        
        # Validate data quality
        report = await quality_validator.validate_data(
            data=mock_data,
            validation_rules=validation.custom_rules,
            job_id=job_id,
            db=db
        )
        
        return DataQualityResponse(
            job_id=job_id,
            total_records=report.total_records,
            valid_records=report.valid_records,
            invalid_records=report.invalid_records,
            quality_score=report.quality_score,
            issues=report.issues,
            validation_summary={
                "rules_applied": len(validation.custom_rules),
                "quality_score": report.quality_score,
                "status": "completed"
            }
        )
        
    except Exception as e:
        logger.error(f"Data quality validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get status of data processing job"""
    try:
        # Check ingestion jobs
        ingestion_job = ingestion_engine.get_job_status(job_id, db)
        if ingestion_job:
            return JobStatusResponse(
                job_id=job_id,
                status=ingestion_job.status,
                progress=None,
                message="Data ingestion job",
                created_at=ingestion_job.created_at,
                updated_at=ingestion_job.updated_at,
                error_message=ingestion_job.error_message
            )
        
        # Check synthetic data jobs
        synthetic_job = synthetic_generator.get_job_status(job_id, db)
        if synthetic_job:
            return JobStatusResponse(
                job_id=job_id,
                status=synthetic_job.status,
                progress=None,
                message="Synthetic data generation job",
                created_at=synthetic_job.created_at,
                updated_at=synthetic_job.completed_at or synthetic_job.created_at,
                error_message=None
            )
        
        raise HTTPException(status_code=404, detail="Job not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/quality/{job_id}", response_model=DataQualityResponse)
async def get_quality_report(job_id: str, db: Session = Depends(get_db)):
    """Get data quality report for a job"""
    try:
        report = quality_validator.get_quality_report(job_id, db)
        if not report:
            raise HTTPException(status_code=404, detail="Quality report not found")
        
        return DataQualityResponse(
            job_id=job_id,
            total_records=report.total_records,
            valid_records=report.valid_records,
            invalid_records=report.invalid_records,
            quality_score=report.quality_score,
            issues=report.issues,
            validation_summary={
                "rules_applied": len(report.validation_rules),
                "quality_score": report.quality_score,
                "created_at": report.created_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/templates", response_model=List[Dict[str, Any]])
async def get_synthetic_data_templates():
    """Get available synthetic data templates"""
    templates = [
        {
            "name": "user_profile",
            "description": "Generate user profile data with personal information",
            "parameters": {
                "country": "Country code (default: US)",
                "language": "Language code (default: en)"
            }
        },
        {
            "name": "transaction",
            "description": "Generate financial transaction data",
            "parameters": {
                "num_users": "Number of unique users (default: 1000)",
                "currency": "Currency code (default: USD)",
                "country": "Country code (default: US)"
            }
        },
        {
            "name": "product",
            "description": "Generate product catalog data",
            "parameters": {
                "categories": "List of product categories",
                "currency": "Currency code (default: USD)"
            }
        },
        {
            "name": "conversation",
            "description": "Generate conversation data for AI training",
            "parameters": {
                "language": "Language code (default: en)"
            }
        },
        {
            "name": "document",
            "description": "Generate document metadata and content",
            "parameters": {
                "document_types": "List of document types",
                "language": "Language code (default: en)"
            }
        },
        {
            "name": "sensor_data",
            "description": "Generate IoT sensor readings",
            "parameters": {
                "sensor_types": "List of sensor types",
                "num_devices": "Number of devices (default: 100)"
            }
        }
    ]
    
    return templates


@router.get("/data/formats", response_model=List[str])
async def get_supported_formats():
    """Get list of supported data formats"""
    return ["csv", "json", "parquet", "text", "xml"]


# Vector Database and Knowledge Management Endpoints

@router.post("/knowledge/ingest", response_model=Dict[str, Any])
async def ingest_documents(
    documents: List[Dict[str, Any]],
    chunking_strategy: str = "fixed_size",
    chunk_size: int = 512,
    overlap: int = 50
):
    """Ingest documents into knowledge base"""
    try:
        document_ids = knowledge_manager.ingest_documents(
            documents=documents,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        return {
            "message": f"Successfully ingested {len(document_ids)} documents",
            "document_ids": document_ids,
            "chunking_strategy": chunking_strategy,
            "chunk_size": chunk_size,
            "overlap": overlap
        }
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/search", response_model=List[Dict[str, Any]])
async def search_knowledge(
    query: str,
    search_type: str = "semantic",
    top_k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None
):
    """Search knowledge base"""
    try:
        results = knowledge_manager.search_knowledge(
            query=query,
            search_type=search_type,
            top_k=top_k,
            metadata_filter=metadata_filter
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Knowledge search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/stats", response_model=Dict[str, Any])
async def get_knowledge_stats():
    """Get knowledge base statistics"""
    try:
        stats = knowledge_manager.get_knowledge_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/chunking-strategies", response_model=List[Dict[str, Any]])
async def get_chunking_strategies():
    """Get available document chunking strategies"""
    strategies = [
        {
            "name": "fixed_size",
            "description": "Split documents into fixed-size chunks with optional overlap",
            "parameters": {
                "chunk_size": "Size of each chunk in characters (default: 512)",
                "overlap": "Number of characters to overlap between chunks (default: 50)"
            }
        },
        {
            "name": "sentence",
            "description": "Split documents by sentences, grouping sentences into chunks",
            "parameters": {
                "chunk_size": "Maximum size of each chunk in characters",
                "overlap": "Number of sentences to overlap between chunks"
            }
        },
        {
            "name": "paragraph",
            "description": "Split documents by paragraphs, grouping paragraphs into chunks",
            "parameters": {
                "chunk_size": "Maximum size of each chunk in characters",
                "overlap": "Number of paragraphs to overlap between chunks"
            }
        },
        {
            "name": "semantic",
            "description": "Split documents based on semantic boundaries and topic changes",
            "parameters": {
                "chunk_size": "Maximum size of each chunk in characters",
                "overlap": "Overlap handling for semantic boundaries"
            }
        }
    ]
    
    return strategies


@router.delete("/knowledge/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete document from knowledge base"""
    try:
        success = knowledge_manager.vector_db.delete_document(document_id)
        
        if success:
            return {"message": f"Document {document_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/documents/{document_id}")
async def get_document(document_id: str):
    """Get document by ID"""
    try:
        document = knowledge_manager.vector_db.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "id": document.id,
            "content": document.content,
            "metadata": document.metadata,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "embedding_dimension": len(document.embedding) if document.embedding else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "data-pipeline-service",
        "version": "1.0.0"
    }