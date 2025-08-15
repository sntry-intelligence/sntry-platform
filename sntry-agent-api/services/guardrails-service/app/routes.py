"""
AI Guardrails service API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import logging

from .models import (
    ContentModerationRequest, ContentModerationResponse,
    BiasDetectionRequest, BiasDetectionResponse,
    ResponseValidationRequest, ResponseValidationResponse,
    GuardrailsConfigRequest, GuardrailsConfigResponse,
    GuardrailsStatsResponse, ContentModerationLog, BiasDetectionLog,
    GuardrailsConfig, ViolationType, SeverityLevel
)
from .guardrails import ContentModerator, BiasDetector, ResponseValidator, generate_content_hash
from .database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize guardrails components
content_moderator = ContentModerator()
bias_detector = BiasDetector()
response_validator = ResponseValidator()


@router.post("/guardrails/content/moderate", response_model=ContentModerationResponse)
async def moderate_content(
    request: ContentModerationRequest,
    db: Session = Depends(get_db)
):
    """Moderate content for safety and appropriateness"""
    try:
        request_id = str(uuid.uuid4())
        
        # Perform content moderation
        moderation_result = content_moderator.moderate_content(
            request.content,
            request.context
        )
        
        # Log the moderation result
        content_hash = generate_content_hash(request.content)
        
        # Determine primary violation if any
        primary_violation = None
        if moderation_result['violations']:
            primary_violation = max(
                moderation_result['violations'],
                key=lambda x: x['confidence']
            )
        
        log_entry = ContentModerationLog(
            content_hash=content_hash,
            content_type=request.content_type,
            violation_type=primary_violation['type'] if primary_violation else None,
            severity=primary_violation['severity'] if primary_violation else None,
            confidence_score=moderation_result['confidence_score'],
            action_taken=moderation_result['action'],
            model_used="content_moderator_v1",
            extra_data={
                'user_id': request.user_id,
                'session_id': request.session_id,
                'context': request.context,
                'all_violations': moderation_result['violations']
            }
        )
        
        db.add(log_entry)
        db.commit()
        
        return ContentModerationResponse(
            is_safe=moderation_result['is_safe'],
            violations=moderation_result['violations'],
            action=moderation_result['action'],
            confidence_score=moderation_result['confidence_score'],
            filtered_content=moderation_result['filtered_content'],
            explanation=moderation_result['explanation'],
            request_id=request_id
        )
    
    except Exception as e:
        logger.error(f"Content moderation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content moderation failed: {str(e)}"
        )


@router.post("/guardrails/bias/detect", response_model=BiasDetectionResponse)
async def detect_bias(
    request: BiasDetectionRequest,
    db: Session = Depends(get_db)
):
    """Detect bias in content"""
    try:
        request_id = str(uuid.uuid4())
        
        # Perform bias detection
        bias_result = bias_detector.detect_bias(
            request.content,
            request.bias_types
        )
        
        # Log bias detection results
        content_hash = generate_content_hash(request.content)
        
        for bias_info in bias_result['bias_results']:
            log_entry = BiasDetectionLog(
                content_hash=content_hash,
                bias_type=bias_info['bias_type'],
                bias_score=bias_info['score'],
                confidence_score=bias_info['confidence'],
                detected_terms=[e.get('word', e.get('match', '')) for e in bias_info['evidence']],
                context=request.content[:500],  # Store first 500 chars as context
                model_used="bias_detector_v1",
                extra_data={
                    'evidence': bias_info['evidence'],
                    'context': request.context
                }
            )
            db.add(log_entry)
        
        db.commit()
        
        return BiasDetectionResponse(
            has_bias=bias_result['has_bias'],
            bias_results=bias_result['bias_results'],
            overall_bias_score=bias_result['overall_bias_score'],
            confidence_score=bias_result['confidence_score'],
            recommendations=bias_result['recommendations'],
            request_id=request_id
        )
    
    except Exception as e:
        logger.error(f"Bias detection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bias detection failed: {str(e)}"
        )


@router.post("/guardrails/validate", response_model=ResponseValidationResponse)
async def validate_response(
    request: ResponseValidationRequest,
    db: Session = Depends(get_db)
):
    """Validate AI response for safety and appropriateness"""
    try:
        request_id = str(uuid.uuid4())
        
        # Perform response validation
        validation_result = response_validator.validate_response(
            request.response_text,
            request.prompt,
            request.context,
            request.validation_rules
        )
        
        # Log validation results (using content moderation log for now)
        content_hash = generate_content_hash(request.response_text)
        
        log_entry = ContentModerationLog(
            content_hash=content_hash,
            content_type="ai_response",
            violation_type="validation_failure" if not validation_result['is_valid'] else None,
            severity=SeverityLevel.MEDIUM if not validation_result['is_valid'] else None,
            confidence_score=validation_result['confidence_score'],
            action_taken="review" if not validation_result['is_valid'] else "allow",
            model_used="response_validator_v1",
            extra_data={
                'prompt': request.prompt,
                'context': request.context,
                'validation_rules': request.validation_rules,
                'validation_results': validation_result['validation_results'],
                'issues_found': validation_result['issues_found']
            }
        )
        
        db.add(log_entry)
        db.commit()
        
        return ResponseValidationResponse(
            is_valid=validation_result['is_valid'],
            validation_results=validation_result['validation_results'],
            issues_found=validation_result['issues_found'],
            suggestions=validation_result['suggestions'],
            confidence_score=validation_result['confidence_score'],
            request_id=request_id
        )
    
    except Exception as e:
        logger.error(f"Response validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response validation failed: {str(e)}"
        )


# Configuration management endpoints
@router.post("/guardrails/configs", response_model=GuardrailsConfigResponse)
async def create_config(
    config_request: GuardrailsConfigRequest,
    db: Session = Depends(get_db)
):
    """Create a new guardrails configuration"""
    # Check if config with same name exists
    existing_config = db.query(GuardrailsConfig).filter(
        GuardrailsConfig.name == config_request.name
    ).first()
    
    if existing_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration with this name already exists"
        )
    
    config = GuardrailsConfig(
        name=config_request.name,
        description=config_request.description,
        config_data=config_request.config_data
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return GuardrailsConfigResponse.from_orm(config)


@router.get("/guardrails/configs", response_model=List[GuardrailsConfigResponse])
async def list_configs(
    active_only: bool = Query(True, description="Return only active configurations"),
    db: Session = Depends(get_db)
):
    """List all guardrails configurations"""
    query = db.query(GuardrailsConfig)
    
    if active_only:
        query = query.filter(GuardrailsConfig.is_active == True)
    
    configs = query.all()
    return [GuardrailsConfigResponse.from_orm(config) for config in configs]


@router.get("/guardrails/configs/{config_id}", response_model=GuardrailsConfigResponse)
async def get_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific guardrails configuration"""
    config = db.query(GuardrailsConfig).filter(GuardrailsConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    return GuardrailsConfigResponse.from_orm(config)


@router.put("/guardrails/configs/{config_id}", response_model=GuardrailsConfigResponse)
async def update_config(
    config_id: int,
    config_request: GuardrailsConfigRequest,
    db: Session = Depends(get_db)
):
    """Update a guardrails configuration"""
    config = db.query(GuardrailsConfig).filter(GuardrailsConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    config.name = config_request.name
    config.description = config_request.description
    config.config_data = config_request.config_data
    
    db.commit()
    db.refresh(config)
    
    return GuardrailsConfigResponse.from_orm(config)


@router.delete("/guardrails/configs/{config_id}")
async def delete_config(
    config_id: int,
    db: Session = Depends(get_db)
):
    """Delete a guardrails configuration"""
    config = db.query(GuardrailsConfig).filter(GuardrailsConfig.id == config_id).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )
    
    db.delete(config)
    db.commit()
    
    return {"message": "Configuration deleted successfully"}


# Statistics and monitoring endpoints
@router.get("/guardrails/stats", response_model=GuardrailsStatsResponse)
async def get_guardrails_stats(
    days: int = Query(7, description="Number of days to include in statistics"),
    db: Session = Depends(get_db)
):
    """Get guardrails usage statistics"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get content moderation stats
    total_requests = db.query(ContentModerationLog).filter(
        ContentModerationLog.created_at >= start_date
    ).count()
    
    violations_detected = db.query(ContentModerationLog).filter(
        ContentModerationLog.created_at >= start_date,
        ContentModerationLog.violation_type.isnot(None)
    ).count()
    
    violation_rate = violations_detected / total_requests if total_requests > 0 else 0.0
    
    # Get top violations
    top_violations_query = db.query(
        ContentModerationLog.violation_type,
        db.func.count(ContentModerationLog.violation_type).label('count')
    ).filter(
        ContentModerationLog.created_at >= start_date,
        ContentModerationLog.violation_type.isnot(None)
    ).group_by(ContentModerationLog.violation_type).order_by(
        db.func.count(ContentModerationLog.violation_type).desc()
    ).limit(5).all()
    
    top_violations = [
        {'violation_type': vtype, 'count': count}
        for vtype, count in top_violations_query
    ]
    
    # Get bias detection stats
    bias_detections = db.query(BiasDetectionLog).filter(
        BiasDetectionLog.created_at >= start_date
    ).count()
    
    # Response validation stats (from content moderation log with ai_response type)
    response_validations = db.query(ContentModerationLog).filter(
        ContentModerationLog.created_at >= start_date,
        ContentModerationLog.content_type == "ai_response"
    ).count()
    
    return GuardrailsStatsResponse(
        total_requests=total_requests,
        violations_detected=violations_detected,
        violation_rate=violation_rate,
        top_violations=top_violations,
        bias_detections=bias_detections,
        response_validations=response_validations,
        period_start=start_date,
        period_end=end_date
    )


# Health check and utility endpoints
@router.get("/guardrails/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "guardrails-service",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "content_moderator": "active",
            "bias_detector": "active",
            "response_validator": "active"
        }
    }


@router.post("/guardrails/test")
async def test_guardrails():
    """Test endpoint to verify guardrails functionality"""
    test_content = "This is a test message to verify the guardrails are working properly."
    
    # Test content moderation
    moderation_result = content_moderator.moderate_content(test_content)
    
    # Test bias detection
    bias_result = bias_detector.detect_bias(test_content)
    
    # Test response validation
    validation_result = response_validator.validate_response(
        test_content,
        "Generate a test response",
        None,
        ["max_length_500"]
    )
    
    return {
        "message": "Guardrails test completed",
        "results": {
            "content_moderation": {
                "is_safe": moderation_result['is_safe'],
                "violations_count": len(moderation_result['violations'])
            },
            "bias_detection": {
                "has_bias": bias_result['has_bias'],
                "bias_score": bias_result['overall_bias_score']
            },
            "response_validation": {
                "is_valid": validation_result['is_valid'],
                "confidence": validation_result['confidence_score']
            }
        }
    }