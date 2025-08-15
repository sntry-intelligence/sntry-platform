from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class EvaluationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MetricType(str, Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    RESPONSE_TIME = "response_time"
    RELEVANCE = "relevance"
    COHERENCE = "coherence"
    FACTUALITY = "factuality"
    CUSTOM = "custom"


class EvaluationMetric(BaseModel):
    """Evaluation metric definition"""
    name: str
    type: MetricType
    description: str
    weight: float = 1.0
    threshold: Optional[float] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TestCase(BaseModel):
    """Individual test case"""
    id: str
    input: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TestDataset(BaseModel):
    """Test dataset definition"""
    id: str
    name: str
    description: Optional[str] = None
    test_cases: List[TestCase]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class EvaluationResult(BaseModel):
    """Result of a single evaluation"""
    test_case_id: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    actual_output: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationSummary(BaseModel):
    """Summary of evaluation results"""
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_metrics: Dict[str, float] = Field(default_factory=dict)
    metric_distributions: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    execution_time_ms: int
    error_analysis: Dict[str, Any] = Field(default_factory=dict)


class Evaluation(BaseModel):
    """Evaluation model"""
    id: str
    agent_id: str
    name: str
    description: Optional[str] = None
    test_dataset_id: Optional[str] = None
    metrics: List[EvaluationMetric] = Field(default_factory=list)
    status: EvaluationStatus
    results: Optional[List[EvaluationResult]] = None
    summary: Optional[EvaluationSummary] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class EvaluationCreateRequest(BaseModel):
    """Request model for creating an evaluation"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    test_dataset_id: Optional[str] = None
    metrics: List[EvaluationMetric] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class EvaluationUpdateRequest(BaseModel):
    """Request model for updating an evaluation"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    metrics: Optional[List[EvaluationMetric]] = None


class EvaluationExecuteRequest(BaseModel):
    """Request model for executing an evaluation"""
    test_dataset_id: Optional[str] = None
    test_cases: Optional[List[TestCase]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TestDatasetCreateRequest(BaseModel):
    """Request model for creating a test dataset"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    test_cases: List[TestCase] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResponse(BaseModel):
    """Response model for evaluation operations"""
    evaluation: Evaluation


class EvaluationListResponse(BaseModel):
    """Response model for listing evaluations"""
    evaluations: List[Evaluation]
    total: int


class TestDatasetResponse(BaseModel):
    """Response model for test dataset operations"""
    dataset: TestDataset


class TestDatasetListResponse(BaseModel):
    """Response model for listing test datasets"""
    datasets: List[TestDataset]
    total: int


class EvaluationResultsResponse(BaseModel):
    """Response model for evaluation results"""
    evaluation_id: str
    results: List[EvaluationResult]
    summary: EvaluationSummary
    status: EvaluationStatus