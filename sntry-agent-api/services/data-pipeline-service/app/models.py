from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

Base = declarative_base()


class DataSourceType(str, Enum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    TEXT = "text"
    XML = "xml"
    DATABASE = "database"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DataIngestionJob(Base):
    __tablename__ = "data_ingestion_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    source_type = Column(String)
    source_path = Column(String)
    status = Column(String, default=ProcessingStatus.PENDING)
    job_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, index=True)
    total_records = Column(Integer)
    valid_records = Column(Integer)
    invalid_records = Column(Integer)
    quality_score = Column(Float)
    validation_rules = Column(JSON)
    issues = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class SyntheticDataJob(Base):
    __tablename__ = "synthetic_data_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    template_type = Column(String)
    parameters = Column(JSON)
    output_format = Column(String)
    records_generated = Column(Integer, default=0)
    status = Column(String, default=ProcessingStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Pydantic models for API requests/responses
class DataIngestionRequest(BaseModel):
    source_type: DataSourceType
    source_path: str
    metadata: Optional[Dict[str, Any]] = {}
    validation_rules: Optional[List[str]] = []


class DataCleaningRequest(BaseModel):
    job_id: str
    cleaning_operations: List[str] = Field(default_factory=list)
    remove_duplicates: bool = True
    handle_missing_values: str = "drop"  # drop, fill, interpolate
    normalize_text: bool = True


class SyntheticDataRequest(BaseModel):
    template_type: str
    num_records: int = Field(gt=0, le=100000)
    output_format: DataSourceType = DataSourceType.JSON
    parameters: Dict[str, Any] = Field(default_factory=dict)
    preserve_privacy: bool = True


class DataQualityValidation(BaseModel):
    required_columns: List[str] = Field(default_factory=list)
    data_types: Dict[str, str] = Field(default_factory=dict)
    value_ranges: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    regex_patterns: Dict[str, str] = Field(default_factory=dict)
    custom_rules: List[str] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    job_id: str
    status: ProcessingStatus
    progress: Optional[float] = None
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None


class DataQualityResponse(BaseModel):
    job_id: str
    total_records: int
    valid_records: int
    invalid_records: int
    quality_score: float
    issues: List[Dict[str, Any]]
    validation_summary: Dict[str, Any]