"""
AI Guardrails service data models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

Base = declarative_base()


class ViolationType(str, Enum):
    """Types of content violations"""
    HATE_SPEECH = "hate_speech"
    HARASSMENT = "harassment"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SEXUAL_CONTENT = "sexual_content"
    PROFANITY = "profanity"
    SPAM = "spam"
    MISINFORMATION = "misinformation"
    BIAS = "bias"
    TOXICITY = "toxicity"
    PII = "pii"  # Personally Identifiable Information


class SeverityLevel(str, Enum):
    """Severity levels for violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(str, Enum):
    """Actions to take on violations"""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    FILTER = "filter"
    ESCALATE = "escalate"


# Database Models
class ContentModerationLog(Base):
    """Log of content moderation actions"""
    __tablename__ = "content_moderation_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String, index=True)  # Hash of the content for deduplication
    content_type = Column(String, nullable=False)  # text, image, audio, etc.
    violation_type = Column(String)  # ViolationType enum
    severity = Column(String)  # SeverityLevel enum
    confidence_score = Column(Float)  # 0.0 to 1.0
    action_taken = Column(String)  # ActionType enum
    model_used = Column(String)  # Which model/service was used for detection
    extra_data = Column(JSON)  # Additional context and details
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BiasDetectionLog(Base):
    """Log of bias detection results"""
    __tablename__ = "bias_detection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String, index=True)
    bias_type = Column(String)  # gender, race, age, religion, etc.
    bias_score = Column(Float)  # 0.0 to 1.0
    confidence_score = Column(Float)  # 0.0 to 1.0
    detected_terms = Column(JSON)  # List of problematic terms/phrases
    context = Column(Text)  # Surrounding context
    model_used = Column(String)
    extra_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GuardrailsConfig(Base):
    """Configuration for guardrails policies"""
    __tablename__ = "guardrails_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    config_data = Column(JSON, nullable=False)  # Policy configuration
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic Models for API
class ContentModerationRequest(BaseModel):
    content: str
    content_type: str = "text"
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class ContentModerationResponse(BaseModel):
    is_safe: bool
    violations: List[Dict[str, Any]] = []
    action: ActionType
    confidence_score: float
    filtered_content: Optional[str] = None
    explanation: Optional[str] = None
    request_id: str


class BiasDetectionRequest(BaseModel):
    content: str
    context: Optional[Dict[str, Any]] = None
    bias_types: Optional[List[str]] = None  # Specific bias types to check


class BiasDetectionResponse(BaseModel):
    has_bias: bool
    bias_results: List[Dict[str, Any]] = []
    overall_bias_score: float
    confidence_score: float
    recommendations: List[str] = []
    request_id: str


class ResponseValidationRequest(BaseModel):
    response_text: str
    prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    validation_rules: Optional[List[str]] = None


class ResponseValidationResponse(BaseModel):
    is_valid: bool
    validation_results: List[Dict[str, Any]] = []
    issues_found: List[str] = []
    suggestions: List[str] = []
    confidence_score: float
    request_id: str


class GuardrailsConfigRequest(BaseModel):
    name: str
    description: Optional[str] = None
    config_data: Dict[str, Any]


class GuardrailsConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    config_data: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class GuardrailsStatsResponse(BaseModel):
    total_requests: int
    violations_detected: int
    violation_rate: float
    top_violations: List[Dict[str, Any]]
    bias_detections: int
    response_validations: int
    period_start: datetime
    period_end: datetime