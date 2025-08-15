from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class WorkflowType(str, Enum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    LOOP = "LOOP"
    DYNAMIC = "DYNAMIC"


class WorkflowStatus(str, Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowStep(BaseModel):
    """Individual workflow step definition"""
    id: str
    name: str
    agent_role: Optional[str] = None
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    timeout: Optional[int] = None  # seconds
    retry_config: Dict[str, Any] = Field(default_factory=dict)


class DynamicRoutingConfig(BaseModel):
    """Configuration for dynamic workflow routing"""
    routing_model: str
    routing_prompt: str
    decision_criteria: Dict[str, Any] = Field(default_factory=dict)


class ErrorHandlingStrategy(BaseModel):
    """Error handling configuration for workflows"""
    retry_attempts: int = 3
    retry_delay: int = 1  # seconds
    fallback_action: Optional[str] = None
    escalation_rules: Dict[str, Any] = Field(default_factory=dict)


class AgentRoleMapping(BaseModel):
    """Mapping of agent roles in workflow"""
    role: str
    agent_id: str
    capabilities: List[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    """Complete workflow definition"""
    type: WorkflowType
    steps: List[WorkflowStep]
    agent_roles: List[AgentRoleMapping] = Field(default_factory=list)
    routing_logic: Optional[DynamicRoutingConfig] = None
    error_handling: ErrorHandlingStrategy = Field(default_factory=ErrorHandlingStrategy)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Result of a workflow step execution"""
    step_id: str
    status: ExecutionStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None


class WorkflowExecution(BaseModel):
    """Workflow execution instance"""
    id: str
    workflow_id: str
    status: ExecutionStatus
    parameters: Dict[str, Any] = Field(default_factory=dict)
    results: List[StepResult] = Field(default_factory=list)
    current_step: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class Workflow(BaseModel):
    """Workflow model"""
    id: str
    agent_id: str
    name: str
    description: Optional[str] = None
    type: WorkflowType
    definition: WorkflowDefinition
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime


class WorkflowCreateRequest(BaseModel):
    """Request model for creating a workflow"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    definition: WorkflowDefinition


class WorkflowUpdateRequest(BaseModel):
    """Request model for updating a workflow"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    definition: Optional[WorkflowDefinition] = None


class WorkflowExecutionRequest(BaseModel):
    """Request model for executing a workflow"""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = None  # seconds


class WorkflowResponse(BaseModel):
    """Response model for workflow operations"""
    workflow: Workflow


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows"""
    workflows: List[Workflow]
    total: int


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution operations"""
    execution: WorkflowExecution