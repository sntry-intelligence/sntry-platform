from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class AgentType(str, Enum):
    PROMPT_BASED = "prompt_based"
    FINE_TUNED = "fine_tuned"
    RL_TRAINED = "rl_trained"


class TrainingType(str, Enum):
    PROMPT_ENGINEERING = "prompt_engineering"
    FINE_TUNING = "fine_tuning"
    RL_TRAINING = "rl_training"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseEntity(BaseModel):
    """Base model with common fields"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class MemoryConfig(BaseModel):
    """Configuration for agent memory"""
    max_context_length: int = 4096
    enable_long_term_memory: bool = True
    memory_type: str = "vector"


class AgentConfig(BaseEntity):
    """Agent configuration model"""
    name: str
    type: AgentType
    model_id: str
    capabilities: List[str] = []
    tools: List[str] = []
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig)


class TrainingConfig(BaseModel):
    """Base training configuration"""
    learning_rate: float = 1e-4
    batch_size: int = 32
    max_epochs: int = 10
    early_stopping: bool = True


class TrainingJob(BaseEntity):
    """Training job model"""
    type: TrainingType
    status: JobStatus = JobStatus.PENDING
    config: TrainingConfig
    metrics: Dict[str, float] = {}
    error_message: Optional[str] = None


class Tool(BaseEntity):
    """Tool definition for MCP"""
    name: str
    description: str
    parameters: Dict[str, Any] = {}
    endpoint: str
    auth_required: bool = False


class Message(BaseModel):
    """Message in a conversation thread"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    sender_id: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


class Thread(BaseEntity):
    """Conversation thread for ACP"""
    participants: List[str] = []
    messages: List[Message] = []
    context: Dict[str, Any] = {}