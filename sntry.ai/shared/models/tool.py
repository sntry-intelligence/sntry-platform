from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ERROR = "ERROR"


class ParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class FunctionParameter(BaseModel):
    """Function parameter definition"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None


class FunctionSignature(BaseModel):
    """Tool function signature definition"""
    name: str
    description: str
    parameters: List[FunctionParameter] = Field(default_factory=list)
    return_type: Optional[str] = None
    return_description: Optional[str] = None


class ConnectionConfig(BaseModel):
    """Tool connection configuration"""
    type: str  # http, grpc, database, etc.
    endpoint: Optional[str] = None
    authentication: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 30  # seconds
    retry_config: Dict[str, Any] = Field(default_factory=dict)


class SecurityPolicy(BaseModel):
    """Tool security policy"""
    allowed_users: List[str] = Field(default_factory=list)
    allowed_roles: List[str] = Field(default_factory=list)
    rate_limit: Optional[int] = None
    require_approval: bool = False
    audit_logging: bool = True
    data_classification: str = "internal"


class InvocationContext(BaseModel):
    """Context for tool invocation"""
    user_id: str
    session_id: Optional[str] = None
    agent_id: str
    workflow_id: Optional[str] = None
    correlation_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Complete tool definition"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    function_signature: FunctionSignature
    connection_details: ConnectionConfig
    security_policy: SecurityPolicy = Field(default_factory=SecurityPolicy)
    mcp_server_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolInvocation(BaseModel):
    """Tool invocation record"""
    id: str
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: InvocationContext
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"
    duration: Optional[int] = None  # milliseconds
    created_at: datetime
    completed_at: Optional[datetime] = None


class Tool(BaseModel):
    """Tool model"""
    id: str
    agent_id: str
    name: str
    description: Optional[str] = None
    function_signature: Dict[str, Any]
    connection_details: Dict[str, Any]
    security_policy: Dict[str, Any]
    mcp_server_id: Optional[str] = None
    status: ToolStatus
    created_at: datetime
    updated_at: datetime


class ToolCreateRequest(BaseModel):
    """Request model for creating a tool"""
    definition: ToolDefinition


class ToolUpdateRequest(BaseModel):
    """Request model for updating a tool"""
    definition: ToolDefinition


class ToolInvocationRequest(BaseModel):
    """Request model for tool invocation"""
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: InvocationContext
    timeout: Optional[int] = None


class ToolResponse(BaseModel):
    """Response model for tool operations"""
    tool: Tool


class ToolListResponse(BaseModel):
    """Response model for listing tools"""
    tools: List[Tool]
    total: int


class ToolInvocationResponse(BaseModel):
    """Response model for tool invocation operations"""
    invocation: ToolInvocation