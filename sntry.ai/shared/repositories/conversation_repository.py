from typing import Any, Dict, List, Optional
from prisma import Prisma
from prisma.models import ConversationSession, Message
from shared.models.base import PaginationParams
from shared.models.conversation import SessionStatus, MessageRole
from .base import CacheableRepository, AuditableRepository


class ConversationSessionRepository(CacheableRepository[ConversationSession], AuditableRepository[ConversationSession]):
    """Repository for ConversationSession entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=300)  # 5 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> ConversationSession:
        """Create a new conversation session"""
        session = await self.db.conversationsession.create(data=data)
        
        # Cache the new session
        cache_key = self._get_cache_key("id", session.id)
        await self._set_cache(cache_key, session.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=session.id,
            entity_type="ConversationSession",
            new_data=session.dict()
        )
        
        return session
    
    async def get_by_id(self, id: str) -> Optional[ConversationSession]:
        """Get conversation session by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_session = await self._get_from_cache(cache_key)
        if cached_session:
            return ConversationSession(**cached_session)
        
        # Fetch from database
        session = await self.db.conversationsession.find_unique(where={"id": id})
        if session:
            await self._set_cache(cache_key, session.dict())
        
        return session
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[ConversationSession]:
        """Update conversation session by ID"""
        # Get old data for audit
        old_session = await self.get_by_id(id)
        if not old_session:
            return None
        
        # Update session
        updated_session = await self.db.conversationsession.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="ConversationSession",
            old_data=old_session.dict(),
            new_data=updated_session.dict()
        )
        
        return updated_session
    
    async def delete(self, id: str) -> bool:
        """Delete conversation session by ID"""
        # Get session for audit
        session = await self.get_by_id(id)
        if not session:
            return False
        
        # Delete session (cascade will handle messages)
        await self.db.conversationsession.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="ConversationSession",
            old_data=session.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[ConversationSession], int]:
        """List conversation sessions with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get sessions and total count
        sessions, total = await self.db.conversationsession.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return sessions, total
    
    async def exists(self, id: str) -> bool:
        """Check if conversation session exists"""
        session = await self.db.conversationsession.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return session is not None
    
    async def get_by_agent_id(self, agent_id: str) -> List[ConversationSession]:
        """Get sessions by agent ID"""
        return await self.db.conversationsession.find_many(
            where={"agent_id": agent_id},
            order=[{"last_activity": "desc"}]
        )
    
    async def get_by_user_id(self, user_id: str) -> List[ConversationSession]:
        """Get sessions by user ID"""
        return await self.db.conversationsession.find_many(
            where={"user_id": user_id},
            order=[{"last_activity": "desc"}]
        )
    
    async def get_by_status(self, status: SessionStatus) -> List[ConversationSession]:
        """Get sessions by status"""
        return await self.db.conversationsession.find_many(where={"status": status})
    
    async def update_status(self, id: str, status: SessionStatus) -> Optional[ConversationSession]:
        """Update session status"""
        return await self.update(id, {
            "status": status,
            "last_activity": "now()"
        })
    
    async def update_last_activity(self, id: str) -> Optional[ConversationSession]:
        """Update last activity timestamp"""
        return await self.update(id, {"last_activity": "now()"})
    
    async def get_active_sessions(self, agent_id: str) -> List[ConversationSession]:
        """Get active sessions for an agent"""
        return await self.db.conversationsession.find_many(
            where={
                "agent_id": agent_id,
                "status": SessionStatus.ACTIVE
            },
            order=[{"last_activity": "desc"}]
        )
    
    async def get_sessions_with_messages(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[ConversationSession]:
        """Get sessions with their recent messages"""
        return await self.db.conversationsession.find_many(
            where={"agent_id": agent_id},
            include={
                "messages": {
                    "take": 5,
                    "order_by": {"created_at": "desc"}
                }
            },
            order=[{"last_activity": "desc"}],
            take=limit
        )
    
    async def archive_old_sessions(self, days_old: int = 30) -> int:
        """Archive sessions older than specified days"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Update old sessions to archived status
        result = await self.db.conversationsession.update_many(
            where={
                "last_activity": {"lt": cutoff_date},
                "status": {"not": SessionStatus.ARCHIVED}
            },
            data={"status": SessionStatus.ARCHIVED}
        )
        
        return result.count


class MessageRepository(CacheableRepository[Message], AuditableRepository[Message]):
    """Repository for Message entities"""
    
    def __init__(self, db: Prisma):
        super().__init__(db, cache_ttl=180)  # 3 minutes cache
    
    async def create(self, data: Dict[str, Any]) -> Message:
        """Create a new message"""
        message = await self.db.message.create(data=data)
        
        # Update session last activity
        await self.db.conversationsession.update(
            where={"id": message.session_id},
            data={"last_activity": "now()"}
        )
        
        # Cache the new message
        cache_key = self._get_cache_key("id", message.id)
        await self._set_cache(cache_key, message.dict())
        
        # Create audit log
        await self._create_audit_log(
            action="CREATE",
            entity_id=message.id,
            entity_type="Message",
            new_data=message.dict()
        )
        
        return message
    
    async def get_by_id(self, id: str) -> Optional[Message]:
        """Get message by ID with caching"""
        # Try cache first
        cache_key = self._get_cache_key("id", id)
        cached_message = await self._get_from_cache(cache_key)
        if cached_message:
            return Message(**cached_message)
        
        # Fetch from database
        message = await self.db.message.find_unique(where={"id": id})
        if message:
            await self._set_cache(cache_key, message.dict())
        
        return message
    
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[Message]:
        """Update message by ID"""
        # Get old data for audit
        old_message = await self.get_by_id(id)
        if not old_message:
            return None
        
        # Update message
        updated_message = await self.db.message.update(
            where={"id": id},
            data=data
        )
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="UPDATE",
            entity_id=id,
            entity_type="Message",
            old_data=old_message.dict(),
            new_data=updated_message.dict()
        )
        
        return updated_message
    
    async def delete(self, id: str) -> bool:
        """Delete message by ID"""
        # Get message for audit
        message = await self.get_by_id(id)
        if not message:
            return False
        
        # Delete message
        await self.db.message.delete(where={"id": id})
        
        # Invalidate cache
        await self.invalidate_cache(id)
        
        # Create audit log
        await self._create_audit_log(
            action="DELETE",
            entity_id=id,
            entity_type="Message",
            old_data=message.dict()
        )
        
        return True
    
    async def list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Dict[str, str]] = None
    ) -> tuple[List[Message], int]:
        """List messages with pagination and filtering"""
        skip, take = self._calculate_pagination(pagination)
        where = self._build_where_clause(filters)
        order = self._build_order_by(order_by)
        
        # Get messages and total count
        messages, total = await self.db.message.find_many_and_count(
            where=where,
            skip=skip,
            take=take,
            order=order
        )
        
        return messages, total
    
    async def exists(self, id: str) -> bool:
        """Check if message exists"""
        message = await self.db.message.find_unique(
            where={"id": id},
            select={"id": True}
        )
        return message is not None
    
    async def get_by_session_id(
        self,
        session_id: str,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Message], int]:
        """Get messages by session ID"""
        where = {"session_id": session_id}
        
        if pagination:
            skip, take = self._calculate_pagination(pagination)
            messages, total = await self.db.message.find_many_and_count(
                where=where,
                skip=skip,
                take=take,
                order=[{"created_at": "asc"}]
            )
        else:
            messages = await self.db.message.find_many(
                where=where,
                order=[{"created_at": "asc"}]
            )
            total = len(messages)
        
        return messages, total
    
    async def get_by_role(self, session_id: str, role: MessageRole) -> List[Message]:
        """Get messages by session ID and role"""
        return await self.db.message.find_many(
            where={
                "session_id": session_id,
                "role": role
            },
            order=[{"created_at": "asc"}]
        )
    
    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for a session"""
        return await self.db.message.find_many(
            where={"session_id": session_id},
            order=[{"created_at": "desc"}],
            take=limit
        )
    
    async def search_messages(
        self,
        session_id: str,
        query: str,
        pagination: Optional[PaginationParams] = None
    ) -> tuple[List[Message], int]:
        """Search messages by content"""
        where = {
            "session_id": session_id,
            "content": {"contains": query, "mode": "insensitive"}
        }
        
        if pagination:
            skip, take = self._calculate_pagination(pagination)
            messages, total = await self.db.message.find_many_and_count(
                where=where,
                skip=skip,
                take=take,
                order=[{"created_at": "desc"}]
            )
        else:
            messages = await self.db.message.find_many(
                where=where,
                order=[{"created_at": "desc"}]
            )
            total = len(messages)
        
        return messages, total
    
    async def get_conversation_history(
        self,
        session_id: str,
        include_system: bool = False
    ) -> List[Message]:
        """Get complete conversation history"""
        where = {"session_id": session_id}
        
        if not include_system:
            where["role"] = {"not": MessageRole.SYSTEM}
        
        return await self.db.message.find_many(
            where=where,
            order=[{"created_at": "asc"}]
        )
    
    async def get_messages_with_tool_calls(self, session_id: str) -> List[Message]:
        """Get messages that contain tool calls"""
        return await self.db.message.find_many(
            where={
                "session_id": session_id,
                "tool_calls": {"not": None}
            },
            order=[{"created_at": "asc"}]
        )
    
    async def delete_old_messages(self, session_id: str, keep_count: int = 100) -> int:
        """Delete old messages, keeping only the most recent ones"""
        # Get message IDs to delete
        messages_to_delete = await self.db.message.find_many(
            where={"session_id": session_id},
            select={"id": True},
            order=[{"created_at": "desc"}],
            skip=keep_count
        )
        
        if not messages_to_delete:
            return 0
        
        # Delete old messages
        message_ids = [msg.id for msg in messages_to_delete]
        result = await self.db.message.delete_many(
            where={"id": {"in": message_ids}}
        )
        
        return result.count