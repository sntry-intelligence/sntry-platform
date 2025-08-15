"""
Unit tests for repository classes
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from shared.repositories import (
    AgentRepository,
    WorkflowRepository,
    WorkflowExecutionRepository,
    ToolRepository,
    ToolInvocationRepository,
    ConversationSessionRepository,
    MessageRepository,
    VectorStoreRepository,
    EmbeddingRepository
)
from shared.models import (
    AgentStatus, WorkflowStatus, ExecutionStatus, ToolStatus,
    SessionStatus, MessageRole, VectorStoreStatus, VectorStoreType,
    PaginationParams
)


@pytest.fixture
def mock_db():
    """Mock Prisma database instance"""
    db = MagicMock()
    
    # Mock common methods
    db.agent = MagicMock()
    db.workflow = MagicMock()
    db.workflowexecution = MagicMock()
    db.tool = MagicMock()
    db.toolinvocation = MagicMock()
    db.conversationsession = MagicMock()
    db.message = MagicMock()
    db.vectorstore = MagicMock()
    db.embedding = MagicMock()
    
    return db


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing"""
    return {
        "id": "agent-123",
        "name": "Test Agent",
        "description": "A test agent",
        "model_id": "gpt-4",
        "role": "ASSISTANT",
        "orchestration_type": "SINGLE",
        "status": AgentStatus.CREATED,
        "configuration": {"test": "config"},
        "deployment_info": None,
        "metadata": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing"""
    return {
        "id": "workflow-123",
        "agent_id": "agent-123",
        "name": "Test Workflow",
        "description": "A test workflow",
        "type": "SEQUENTIAL",
        "definition": {"steps": []},
        "status": WorkflowStatus.CREATED,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }


class TestAgentRepository:
    """Test AgentRepository class"""
    
    @pytest.mark.asyncio
    async def test_create_agent(self, mock_db, sample_agent_data):
        """Test creating an agent"""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent.dict.return_value = sample_agent_data
        mock_agent.id = sample_agent_data["id"]
        mock_db.agent.create = AsyncMock(return_value=mock_agent)
        
        # Create repository
        repo = AgentRepository(mock_db)
        
        # Mock cache methods
        repo._set_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test create
        result = await repo.create(sample_agent_data)
        
        # Assertions
        mock_db.agent.create.assert_called_once_with(data=sample_agent_data)
        repo._set_cache.assert_called_once()
        repo._create_audit_log.assert_called_once()
        assert result == mock_agent
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_cache_hit(self, mock_db, sample_agent_data):
        """Test getting agent by ID with cache hit"""
        repo = AgentRepository(mock_db)
        
        # Mock cache hit
        repo._get_from_cache = AsyncMock(return_value=sample_agent_data)
        
        # Test get
        result = await repo.get_by_id("agent-123")
        
        # Assertions
        repo._get_from_cache.assert_called_once()
        mock_db.agent.find_unique.assert_not_called()
        assert result.id == sample_agent_data["id"]
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_cache_miss(self, mock_db, sample_agent_data):
        """Test getting agent by ID with cache miss"""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent.dict.return_value = sample_agent_data
        mock_db.agent.find_unique = AsyncMock(return_value=mock_agent)
        
        repo = AgentRepository(mock_db)
        
        # Mock cache miss
        repo._get_from_cache = AsyncMock(return_value=None)
        repo._set_cache = AsyncMock()
        
        # Test get
        result = await repo.get_by_id("agent-123")
        
        # Assertions
        repo._get_from_cache.assert_called_once()
        mock_db.agent.find_unique.assert_called_once_with(where={"id": "agent-123"})
        repo._set_cache.assert_called_once()
        assert result == mock_agent
    
    @pytest.mark.asyncio
    async def test_update_agent(self, mock_db, sample_agent_data):
        """Test updating an agent"""
        # Setup mocks
        old_agent = MagicMock()
        old_agent.dict.return_value = sample_agent_data
        
        updated_agent = MagicMock()
        updated_data = {**sample_agent_data, "name": "Updated Agent"}
        updated_agent.dict.return_value = updated_data
        
        mock_db.agent.update = AsyncMock(return_value=updated_agent)
        
        repo = AgentRepository(mock_db)
        repo.get_by_id = AsyncMock(return_value=old_agent)
        repo.invalidate_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test update
        update_data = {"name": "Updated Agent"}
        result = await repo.update("agent-123", update_data)
        
        # Assertions
        repo.get_by_id.assert_called_once_with("agent-123")
        mock_db.agent.update.assert_called_once_with(
            where={"id": "agent-123"},
            data=update_data
        )
        repo.invalidate_cache.assert_called_once_with("agent-123")
        repo._create_audit_log.assert_called_once()
        assert result == updated_agent
    
    @pytest.mark.asyncio
    async def test_delete_agent(self, mock_db, sample_agent_data):
        """Test deleting an agent"""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent.dict.return_value = sample_agent_data
        mock_db.agent.delete = AsyncMock()
        
        repo = AgentRepository(mock_db)
        repo.get_by_id = AsyncMock(return_value=mock_agent)
        repo.invalidate_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test delete
        result = await repo.delete("agent-123")
        
        # Assertions
        repo.get_by_id.assert_called_once_with("agent-123")
        mock_db.agent.delete.assert_called_once_with(where={"id": "agent-123"})
        repo.invalidate_cache.assert_called_once_with("agent-123")
        repo._create_audit_log.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_list_agents(self, mock_db):
        """Test listing agents with pagination"""
        # Setup mock
        mock_agents = [MagicMock(), MagicMock()]
        mock_db.agent.find_many_and_count = AsyncMock(return_value=(mock_agents, 2))
        
        repo = AgentRepository(mock_db)
        
        # Test list
        pagination = PaginationParams(page=1, size=10)
        agents, total = await repo.list(pagination)
        
        # Assertions
        mock_db.agent.find_many_and_count.assert_called_once()
        assert len(agents) == 2
        assert total == 2
    
    @pytest.mark.asyncio
    async def test_get_by_status(self, mock_db):
        """Test getting agents by status"""
        # Setup mock
        mock_agents = [MagicMock(), MagicMock()]
        mock_db.agent.find_many = AsyncMock(return_value=mock_agents)
        
        repo = AgentRepository(mock_db)
        
        # Test get by status
        result = await repo.get_by_status(AgentStatus.DEPLOYED)
        
        # Assertions
        mock_db.agent.find_many.assert_called_once_with(
            where={"status": AgentStatus.DEPLOYED}
        )
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_search_agents(self, mock_db):
        """Test searching agents"""
        # Setup mock
        mock_agents = [MagicMock()]
        mock_db.agent.find_many_and_count = AsyncMock(return_value=(mock_agents, 1))
        
        repo = AgentRepository(mock_db)
        
        # Test search
        pagination = PaginationParams(page=1, size=10)
        agents, total = await repo.search_agents("test", pagination)
        
        # Assertions
        mock_db.agent.find_many_and_count.assert_called_once()
        call_args = mock_db.agent.find_many_and_count.call_args
        where_clause = call_args[1]["where"]
        assert "OR" in where_clause
        assert len(agents) == 1
        assert total == 1


class TestWorkflowRepository:
    """Test WorkflowRepository class"""
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, mock_db, sample_workflow_data):
        """Test creating a workflow"""
        # Setup mock
        mock_workflow = MagicMock()
        mock_workflow.dict.return_value = sample_workflow_data
        mock_workflow.id = sample_workflow_data["id"]
        mock_db.workflow.create = AsyncMock(return_value=mock_workflow)
        
        # Create repository
        repo = WorkflowRepository(mock_db)
        
        # Mock cache methods
        repo._set_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test create
        result = await repo.create(sample_workflow_data)
        
        # Assertions
        mock_db.workflow.create.assert_called_once_with(data=sample_workflow_data)
        repo._set_cache.assert_called_once()
        repo._create_audit_log.assert_called_once()
        assert result == mock_workflow
    
    @pytest.mark.asyncio
    async def test_get_by_agent_id(self, mock_db):
        """Test getting workflows by agent ID"""
        # Setup mock
        mock_workflows = [MagicMock(), MagicMock()]
        mock_db.workflow.find_many = AsyncMock(return_value=mock_workflows)
        
        repo = WorkflowRepository(mock_db)
        
        # Test get by agent ID
        result = await repo.get_by_agent_id("agent-123")
        
        # Assertions
        mock_db.workflow.find_many.assert_called_once_with(
            where={"agent_id": "agent-123"}
        )
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_update_status(self, mock_db, sample_workflow_data):
        """Test updating workflow status"""
        # Setup mock
        updated_workflow = MagicMock()
        mock_db.workflow.update = AsyncMock(return_value=updated_workflow)
        
        repo = WorkflowRepository(mock_db)
        repo.update = AsyncMock(return_value=updated_workflow)
        
        # Test update status
        result = await repo.update_status("workflow-123", WorkflowStatus.ACTIVE)
        
        # Assertions
        repo.update.assert_called_once_with(
            "workflow-123",
            {"status": WorkflowStatus.ACTIVE, "updated_at": "now()"}
        )
        assert result == updated_workflow


class TestToolRepository:
    """Test ToolRepository class"""
    
    @pytest.mark.asyncio
    async def test_get_by_agent_id(self, mock_db):
        """Test getting tools by agent ID"""
        # Setup mock
        mock_tools = [MagicMock(), MagicMock()]
        mock_db.tool.find_many = AsyncMock(return_value=mock_tools)
        
        repo = ToolRepository(mock_db)
        
        # Test get by agent ID
        result = await repo.get_by_agent_id("agent-123")
        
        # Assertions
        mock_db.tool.find_many.assert_called_once_with(
            where={"agent_id": "agent-123"}
        )
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_by_name(self, mock_db):
        """Test getting tool by name"""
        # Setup mock
        mock_tool = MagicMock()
        mock_db.tool.find_first = AsyncMock(return_value=mock_tool)
        
        repo = ToolRepository(mock_db)
        
        # Test get by name
        result = await repo.get_by_name("agent-123", "test-tool")
        
        # Assertions
        mock_db.tool.find_first.assert_called_once_with(
            where={"agent_id": "agent-123", "name": "test-tool"}
        )
        assert result == mock_tool


class TestConversationRepository:
    """Test ConversationSessionRepository and MessageRepository"""
    
    @pytest.mark.asyncio
    async def test_create_session(self, mock_db):
        """Test creating a conversation session"""
        # Setup mock
        session_data = {
            "id": "session-123",
            "agent_id": "agent-123",
            "user_id": "user-123",
            "status": SessionStatus.ACTIVE,
            "context": {},
            "metadata": {},
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        
        mock_session = MagicMock()
        mock_session.dict.return_value = session_data
        mock_session.id = session_data["id"]
        mock_db.conversationsession.create = AsyncMock(return_value=mock_session)
        
        repo = ConversationSessionRepository(mock_db)
        repo._set_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test create
        result = await repo.create(session_data)
        
        # Assertions
        mock_db.conversationsession.create.assert_called_once_with(data=session_data)
        repo._set_cache.assert_called_once()
        repo._create_audit_log.assert_called_once()
        assert result == mock_session
    
    @pytest.mark.asyncio
    async def test_create_message_updates_session(self, mock_db):
        """Test that creating a message updates session last activity"""
        # Setup mock
        message_data = {
            "id": "message-123",
            "session_id": "session-123",
            "role": MessageRole.USER,
            "content": "Hello",
            "metadata": {},
            "created_at": datetime.utcnow()
        }
        
        mock_message = MagicMock()
        mock_message.dict.return_value = message_data
        mock_message.id = message_data["id"]
        mock_message.session_id = message_data["session_id"]
        
        mock_db.message.create = AsyncMock(return_value=mock_message)
        mock_db.conversationsession.update = AsyncMock()
        
        repo = MessageRepository(mock_db)
        repo._set_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test create
        result = await repo.create(message_data)
        
        # Assertions
        mock_db.message.create.assert_called_once_with(data=message_data)
        mock_db.conversationsession.update.assert_called_once_with(
            where={"id": "session-123"},
            data={"last_activity": "now()"}
        )
        assert result == mock_message
    
    @pytest.mark.asyncio
    async def test_get_messages_by_session(self, mock_db):
        """Test getting messages by session ID"""
        # Setup mock
        mock_messages = [MagicMock(), MagicMock()]
        mock_db.message.find_many_and_count = AsyncMock(return_value=(mock_messages, 2))
        
        repo = MessageRepository(mock_db)
        
        # Test get by session
        pagination = PaginationParams(page=1, size=10)
        messages, total = await repo.get_by_session_id("session-123", pagination)
        
        # Assertions
        mock_db.message.find_many_and_count.assert_called_once()
        call_args = mock_db.message.find_many_and_count.call_args
        where_clause = call_args[1]["where"]
        assert where_clause == {"session_id": "session-123"}
        assert len(messages) == 2
        assert total == 2


class TestVectorStoreRepository:
    """Test VectorStoreRepository class"""
    
    @pytest.mark.asyncio
    async def test_create_vector_store(self, mock_db):
        """Test creating a vector store"""
        # Setup mock
        store_data = {
            "id": "store-123",
            "name": "Test Store",
            "type": VectorStoreType.PINECONE,
            "configuration": {},
            "status": VectorStoreStatus.CREATED,
            "statistics": {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        mock_store = MagicMock()
        mock_store.dict.return_value = store_data
        mock_store.id = store_data["id"]
        mock_db.vectorstore.create = AsyncMock(return_value=mock_store)
        
        repo = VectorStoreRepository(mock_db)
        repo._set_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test create
        result = await repo.create(store_data)
        
        # Assertions
        mock_db.vectorstore.create.assert_called_once_with(data=store_data)
        repo._set_cache.assert_called_once()
        repo._create_audit_log.assert_called_once()
        assert result == mock_store
    
    @pytest.mark.asyncio
    async def test_get_by_type(self, mock_db):
        """Test getting vector stores by type"""
        # Setup mock
        mock_stores = [MagicMock(), MagicMock()]
        mock_db.vectorstore.find_many = AsyncMock(return_value=mock_stores)
        
        repo = VectorStoreRepository(mock_db)
        
        # Test get by type
        result = await repo.get_by_type(VectorStoreType.PINECONE)
        
        # Assertions
        mock_db.vectorstore.find_many.assert_called_once_with(
            where={"type": VectorStoreType.PINECONE}
        )
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_update_statistics(self, mock_db):
        """Test updating vector store statistics"""
        # Setup mock
        updated_store = MagicMock()
        
        repo = VectorStoreRepository(mock_db)
        repo.update = AsyncMock(return_value=updated_store)
        
        # Test update statistics
        stats = {"total_vectors": 1000, "total_documents": 100}
        result = await repo.update_statistics("store-123", stats)
        
        # Assertions
        repo.update.assert_called_once_with(
            "store-123",
            {"statistics": stats, "updated_at": "now()"}
        )
        assert result == updated_store


class TestEmbeddingRepository:
    """Test EmbeddingRepository class"""
    
    @pytest.mark.asyncio
    async def test_create_embedding_updates_stats(self, mock_db):
        """Test that creating an embedding updates vector store stats"""
        # Setup mock
        embedding_data = {
            "id": "embedding-123",
            "vector_store_id": "store-123",
            "document_id": "doc-123",
            "chunk_index": 0,
            "content": "Test content",
            "metadata": {},
            "vector": [0.1, 0.2, 0.3],
            "created_at": datetime.utcnow()
        }
        
        mock_embedding = MagicMock()
        mock_embedding.dict.return_value = embedding_data
        mock_embedding.id = embedding_data["id"]
        mock_embedding.vector_store_id = embedding_data["vector_store_id"]
        
        mock_db.embedding.create = AsyncMock(return_value=mock_embedding)
        
        repo = EmbeddingRepository(mock_db)
        repo._set_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        repo._update_vector_store_stats = AsyncMock()
        
        # Test create
        result = await repo.create(embedding_data)
        
        # Assertions
        mock_db.embedding.create.assert_called_once_with(data=embedding_data)
        repo._update_vector_store_stats.assert_called_once_with("store-123")
        assert result == mock_embedding
    
    @pytest.mark.asyncio
    async def test_get_by_document_id(self, mock_db):
        """Test getting embeddings by document ID"""
        # Setup mock
        mock_embeddings = [MagicMock(), MagicMock()]
        mock_db.embedding.find_many = AsyncMock(return_value=mock_embeddings)
        
        repo = EmbeddingRepository(mock_db)
        
        # Test get by document ID
        result = await repo.get_by_document_id("store-123", "doc-123")
        
        # Assertions
        mock_db.embedding.find_many.assert_called_once_with(
            where={"vector_store_id": "store-123", "document_id": "doc-123"},
            order=[{"chunk_index": "asc"}]
        )
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_create_batch(self, mock_db):
        """Test creating embeddings in batch"""
        # Setup mock
        embeddings_data = [
            {"vector_store_id": "store-123", "document_id": "doc-1"},
            {"vector_store_id": "store-123", "document_id": "doc-2"}
        ]
        
        mock_embeddings = [MagicMock(), MagicMock()]
        for i, emb in enumerate(mock_embeddings):
            emb.vector_store_id = "store-123"
        
        # Mock transaction
        mock_transaction = MagicMock()
        mock_transaction.embedding.create = AsyncMock(side_effect=mock_embeddings)
        mock_db.tx.return_value.__aenter__ = AsyncMock(return_value=mock_transaction)
        mock_db.tx.return_value.__aexit__ = AsyncMock(return_value=None)
        
        repo = EmbeddingRepository(mock_db)
        repo._update_vector_store_stats = AsyncMock()
        
        # Test batch create
        result = await repo.create_batch(embeddings_data)
        
        # Assertions
        assert len(result) == 2
        repo._update_vector_store_stats.assert_called_once_with("store-123")


class TestRepositoryErrorHandling:
    """Test repository error handling"""
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db):
        """Test getting non-existent record"""
        # Setup mock to return None
        mock_db.agent.find_unique = AsyncMock(return_value=None)
        
        repo = AgentRepository(mock_db)
        repo._get_from_cache = AsyncMock(return_value=None)
        
        # Test get non-existent
        result = await repo.get_by_id("non-existent")
        
        # Assertions
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_non_existent(self, mock_db):
        """Test updating non-existent record"""
        repo = AgentRepository(mock_db)
        repo.get_by_id = AsyncMock(return_value=None)
        
        # Test update non-existent
        result = await repo.update("non-existent", {"name": "Updated"})
        
        # Assertions
        assert result is None
        mock_db.agent.update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_non_existent(self, mock_db):
        """Test deleting non-existent record"""
        repo = AgentRepository(mock_db)
        repo.get_by_id = AsyncMock(return_value=None)
        
        # Test delete non-existent
        result = await repo.delete("non-existent")
        
        # Assertions
        assert result is False
        mock_db.agent.delete.assert_not_called()


class TestCacheIntegration:
    """Test repository cache integration"""
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, mock_db, sample_agent_data):
        """Test that cache is invalidated on update"""
        # Setup mocks
        old_agent = MagicMock()
        old_agent.dict.return_value = sample_agent_data
        
        updated_agent = MagicMock()
        updated_agent.dict.return_value = {**sample_agent_data, "name": "Updated"}
        
        mock_db.agent.update = AsyncMock(return_value=updated_agent)
        
        repo = AgentRepository(mock_db)
        repo.get_by_id = AsyncMock(return_value=old_agent)
        repo.invalidate_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test update
        await repo.update("agent-123", {"name": "Updated"})
        
        # Assertions
        repo.invalidate_cache.assert_called_once_with("agent-123")
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_delete(self, mock_db, sample_agent_data):
        """Test that cache is invalidated on delete"""
        # Setup mock
        mock_agent = MagicMock()
        mock_agent.dict.return_value = sample_agent_data
        mock_db.agent.delete = AsyncMock()
        
        repo = AgentRepository(mock_db)
        repo.get_by_id = AsyncMock(return_value=mock_agent)
        repo.invalidate_cache = AsyncMock()
        repo._create_audit_log = AsyncMock()
        
        # Test delete
        await repo.delete("agent-123")
        
        # Assertions
        repo.invalidate_cache.assert_called_once_with("agent-123")