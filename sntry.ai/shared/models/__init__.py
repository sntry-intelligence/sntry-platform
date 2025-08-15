# Shared Pydantic models

# Base models
from .base import BaseResponse, ErrorResponse, PaginationParams, PaginatedResponse

# Core domain models
from .agent import (
    Agent, AgentStatus, AgentRole, OrchestrationType,
    AgentConfiguration, DeploymentInfo, MemoryConfiguration, EvaluationConfiguration,
    AgentCreateRequest, AgentUpdateRequest, AgentResponse, AgentListResponse
)

from .workflow import (
    Workflow, WorkflowType, WorkflowStatus, ExecutionStatus,
    WorkflowDefinition, WorkflowStep, WorkflowExecution, StepResult,
    DynamicRoutingConfig, ErrorHandlingStrategy, AgentRoleMapping,
    WorkflowCreateRequest, WorkflowUpdateRequest, WorkflowExecutionRequest,
    WorkflowResponse, WorkflowListResponse, WorkflowExecutionResponse
)

from .tool import (
    Tool, ToolStatus, ParameterType,
    ToolDefinition, FunctionSignature, FunctionParameter,
    ConnectionConfig, SecurityPolicy, InvocationContext, ToolInvocation,
    ToolCreateRequest, ToolUpdateRequest, ToolInvocationRequest,
    ToolResponse, ToolListResponse, ToolInvocationResponse
)

from .conversation import (
    ConversationSession, SessionStatus, MessageRole,
    Message, ConversationContext, ToolCall,
    ConversationSessionCreateRequest, ConversationSessionUpdateRequest, MessageCreateRequest,
    ConversationSessionResponse, ConversationSessionListResponse,
    MessageResponse, MessageListResponse, ConversationHistoryResponse
)

from .vector_store import (
    VectorStore, VectorStoreType, VectorStoreStatus,
    VectorStoreConfiguration, IndexingConfig, EmbeddingModelConfig,
    ChunkingStrategy, DataSource, QueryFilter, VectorStoreStats,
    Embedding, VectorQuery, VectorQueryResult,
    VectorStoreCreateRequest, VectorStoreUpdateRequest, EmbeddingIngestionRequest,
    VectorStoreResponse, VectorStoreListResponse, EmbeddingIngestionResponse, VectorQueryResponse
)

from .mcp import (
    MCPServer, MCPServerStatus, ProtocolVersion,
    AuthConfig, MCPTool, DataAccessCapability, MCPCapability, MCPServerCapabilities,
    MCPServerRegistration, MCPServerUpdateRequest, MCPMessage, MCPResponse,
    MCPServerResponse, MCPServerListResponse, MCPCapabilitiesResponse
)

from .evaluation import (
    Evaluation, EvaluationStatus, MetricType,
    EvaluationMetric, TestCase, TestDataset, EvaluationResult, EvaluationSummary,
    EvaluationCreateRequest, EvaluationUpdateRequest, EvaluationExecuteRequest,
    TestDatasetCreateRequest, EvaluationResponse, EvaluationListResponse,
    TestDatasetResponse, TestDatasetListResponse, EvaluationResultsResponse
)

__all__ = [
    # Base models
    "BaseResponse", "ErrorResponse", "PaginationParams", "PaginatedResponse",
    
    # Agent models
    "Agent", "AgentStatus", "AgentRole", "OrchestrationType",
    "AgentConfiguration", "DeploymentInfo", "MemoryConfiguration", "EvaluationConfiguration",
    "AgentCreateRequest", "AgentUpdateRequest", "AgentResponse", "AgentListResponse",
    
    # Workflow models
    "Workflow", "WorkflowType", "WorkflowStatus", "ExecutionStatus",
    "WorkflowDefinition", "WorkflowStep", "WorkflowExecution", "StepResult",
    "DynamicRoutingConfig", "ErrorHandlingStrategy", "AgentRoleMapping",
    "WorkflowCreateRequest", "WorkflowUpdateRequest", "WorkflowExecutionRequest",
    "WorkflowResponse", "WorkflowListResponse", "WorkflowExecutionResponse",
    
    # Tool models
    "Tool", "ToolStatus", "ParameterType",
    "ToolDefinition", "FunctionSignature", "FunctionParameter",
    "ConnectionConfig", "SecurityPolicy", "InvocationContext", "ToolInvocation",
    "ToolCreateRequest", "ToolUpdateRequest", "ToolInvocationRequest",
    "ToolResponse", "ToolListResponse", "ToolInvocationResponse",
    
    # Conversation models
    "ConversationSession", "SessionStatus", "MessageRole",
    "Message", "ConversationContext", "ToolCall",
    "ConversationSessionCreateRequest", "ConversationSessionUpdateRequest", "MessageCreateRequest",
    "ConversationSessionResponse", "ConversationSessionListResponse",
    "MessageResponse", "MessageListResponse", "ConversationHistoryResponse",
    
    # Vector store models
    "VectorStore", "VectorStoreType", "VectorStoreStatus",
    "VectorStoreConfiguration", "IndexingConfig", "EmbeddingModelConfig",
    "ChunkingStrategy", "DataSource", "QueryFilter", "VectorStoreStats",
    "Embedding", "VectorQuery", "VectorQueryResult",
    "VectorStoreCreateRequest", "VectorStoreUpdateRequest", "EmbeddingIngestionRequest",
    "VectorStoreResponse", "VectorStoreListResponse", "EmbeddingIngestionResponse", "VectorQueryResponse",
    
    # MCP models
    "MCPServer", "MCPServerStatus", "ProtocolVersion",
    "AuthConfig", "MCPTool", "DataAccessCapability", "MCPCapability", "MCPServerCapabilities",
    "MCPServerRegistration", "MCPServerUpdateRequest", "MCPMessage", "MCPResponse",
    "MCPServerResponse", "MCPServerListResponse", "MCPCapabilitiesResponse",
    
    # Evaluation models
    "Evaluation", "EvaluationStatus", "MetricType",
    "EvaluationMetric", "TestCase", "TestDataset", "EvaluationResult", "EvaluationSummary",
    "EvaluationCreateRequest", "EvaluationUpdateRequest", "EvaluationExecuteRequest",
    "TestDatasetCreateRequest", "EvaluationResponse", "EvaluationListResponse",
    "TestDatasetResponse", "TestDatasetListResponse", "EvaluationResultsResponse",
]