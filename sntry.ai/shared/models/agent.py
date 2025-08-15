from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    CREATED = "CREATED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class OrchestrationType(str, Enum):
    SINGLE = "SINGLE"
    MULTI_AGENT = "MULTI_AGENT"
    HIERARCHICAL = "HIERARCHICAL"


class AgentRole(str, Enum):
    ASSISTANT = "ASSISTANT"
    SPECIALIST = "SPECIALIST"
    COORDINATOR = "COORDINATOR"
    EVALUATOR = "EVALUATOR"


class MemoryConfiguration(BaseModel):
    """Agent memory configuration"""
    type: str = "conversation"
    max_history: int = 100
    persistence: bool = True
    context_window: int = 4000


class EvaluationConfiguration(BaseModel):
    """Agent evaluation configuration"""
    enabled: bool = True
    metrics: List[str] = ["accuracy", "response_time", "relevance"]
    test_datasets: List[str] = []


class AgentConfiguration(BaseModel):
    """Agent configuration model"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    model_id: str = Field(..., description="LLM model identifier")
    role: AgentRole = AgentRole.ASSISTANT
    orchestration_type: OrchestrationType = OrchestrationType.SINGLE
    memory_config: MemoryConfiguration = Field(default_factory=MemoryConfiguration)
    evaluation_config: Optional[EvaluationConfiguration] = None
    tools: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DeploymentInfo(BaseModel):
    """Agent deployment information"""
    vertex_ai_endpoint: Optional[str] = None
    deployment_id: Optional[str] = None
    resource_pool: Optional[str] = None
    scaling_config: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    """Agent model"""
    id: str
    name: str
    description: Optional[str]
    model_id: str
    role: AgentRole
    orchestration_type: OrchestrationType
    status: AgentStatus
    configuration: Dict[str, Any]
    deployment_info: Optional[DeploymentInfo]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent"""
    configuration: AgentConfiguration


class AgentUpdateRequest(BaseModel):
    """Request model for updating an agent"""
    configuration: AgentConfiguration


class AgentResponse(BaseModel):
    """Response model for agent operations"""
    agent: Agent


class AgentListResponse(BaseModel):
    """Response model for listing agents"""
    agents: List[Agent]
    total: int