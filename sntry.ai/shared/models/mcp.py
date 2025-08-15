from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class MCPServerStatus(str, Enum):
    REGISTERED = "REGISTERED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class ProtocolVersion(str, Enum):
    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class AuthConfig(BaseModel):
    """MCP server authentication configuration"""
    type: str  # bearer, api_key, oauth2, basic
    credentials: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    refresh_config: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataAccessCapability(BaseModel):
    """MCP data access capability"""
    resource_type: str
    operations: List[str]  # read, write, delete, list
    schema: Optional[Dict[str, Any]] = None
    filters: List[str] = Field(default_factory=list)


class MCPCapability(BaseModel):
    """MCP server capability"""
    type: str  # tool, data_access, notification
    name: str
    description: str
    version: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPServerCapabilities(BaseModel):
    """Complete MCP server capabilities"""
    tools: List[MCPTool] = Field(default_factory=list)
    data_access: List[DataAccessCapability] = Field(default_factory=list)
    protocols: List[ProtocolVersion] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPServer(BaseModel):
    """MCP server model"""
    id: str
    name: str
    endpoint_url: str
    authentication_details: Dict[str, Any]
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    security_policy: Dict[str, Any] = Field(default_factory=dict)
    status: MCPServerStatus
    created_at: datetime
    updated_at: datetime


class MCPServerRegistration(BaseModel):
    """MCP server registration request"""
    name: str = Field(..., min_length=1, max_length=100)
    endpoint_url: str = Field(..., description="MCP server endpoint URL")
    authentication_details: AuthConfig
    capabilities: Optional[MCPServerCapabilities] = None
    security_policy: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPServerUpdateRequest(BaseModel):
    """Request model for updating MCP server"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    endpoint_url: Optional[str] = None
    authentication_details: Optional[AuthConfig] = None
    capabilities: Optional[MCPServerCapabilities] = None
    security_policy: Optional[Dict[str, Any]] = None


class MCPMessage(BaseModel):
    """MCP protocol message"""
    id: str
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MCPResponse(BaseModel):
    """MCP protocol response"""
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MCPServerResponse(BaseModel):
    """Response model for MCP server operations"""
    server: MCPServer


class MCPServerListResponse(BaseModel):
    """Response model for listing MCP servers"""
    servers: List[MCPServer]
    total: int


class MCPCapabilitiesResponse(BaseModel):
    """Response model for MCP server capabilities"""
    server_id: str
    capabilities: MCPServerCapabilities
    last_updated: datetime