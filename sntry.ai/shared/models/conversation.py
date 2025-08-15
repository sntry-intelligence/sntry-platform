from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class MessageRole(str, Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"
    TOOL = "TOOL"


class ToolCall(BaseModel):
    """Tool call information in a message"""
    id: str
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None


class ConversationContext(BaseModel):
    """Conversation context and memory"""
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    conversation_summary: Optional[str] = None
    key_entities: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None
    language: str = "en"
    timezone: Optional[str] = None


class Message(BaseModel):
    """Conversation message"""
    id: str
    session_id: str
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: Optional[List[ToolCall]] = None
    created_at: datetime


class ConversationSession(BaseModel):
    """Conversation session model"""
    id: str
    agent_id: str
    user_id: str
    status: SessionStatus
    context: ConversationContext = Field(default_factory=ConversationContext)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_activity: datetime


class ConversationSessionCreateRequest(BaseModel):
    """Request model for creating a conversation session"""
    user_id: str
    context: Optional[ConversationContext] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSessionUpdateRequest(BaseModel):
    """Request model for updating a conversation session"""
    status: Optional[SessionStatus] = None
    context: Optional[ConversationContext] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageCreateRequest(BaseModel):
    """Request model for creating a message"""
    role: MessageRole
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: Optional[List[ToolCall]] = None


class ConversationSessionResponse(BaseModel):
    """Response model for conversation session operations"""
    session: ConversationSession


class ConversationSessionListResponse(BaseModel):
    """Response model for listing conversation sessions"""
    sessions: List[ConversationSession]
    total: int


class MessageResponse(BaseModel):
    """Response model for message operations"""
    message: Message


class MessageListResponse(BaseModel):
    """Response model for listing messages"""
    messages: List[Message]
    total: int


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history"""
    session: ConversationSession
    messages: List[Message]
    total_messages: int