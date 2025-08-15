import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.agent import AgentConfiguration, AgentStatus, AgentRole, OrchestrationType
from services.agent_management.services.agent_service import AgentService


@pytest.fixture
def mock_db():
    """Mock database fixture"""
    db = MagicMock()
    
    # Mock agent creation
    db.agent.create = AsyncMock()
    db.agent.find_unique = AsyncMock()
    db.agent.find_first = AsyncMock()
    db.agent.find_many = AsyncMock()
    db.agent.find_many_and_count = AsyncMock()
    db.agent.update = AsyncMock()
    db.agent.delete = AsyncMock()
    db.agent.count = AsyncMock()
    
    # Mock workflow and conversation counts for deletion checks
    db.workflow.count = AsyncMock(return_value=0)
    db.conversationsession.count = AsyncMock(return_value=0)
    
    return db


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for tests"""
    return AgentConfiguration(
        name="Test Agent",
        description="A test agent",
        model_id="gemini-pro",
        role=AgentRole.ASSISTANT,
        orchestration_type=OrchestrationType.SINGLE,
        tools=[],
        metadata={"test": True}
    )


@pytest.fixture
def mock_agent_data():
    """Mock agent data returned from database"""
    return MagicMock(
        id="test-agent-id",
        name="Test Agent",
        description="A test agent",
        modelId="gemini-pro",
        role="ASSISTANT",
        orchestrationType="SINGLE",
        status="CREATED",
        configuration={},
        deploymentInfo=None,
        metadata={"test": True},
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z"
    )


@pytest.mark.asyncio
async def test_create_agent_success(mock_db, sample_agent_config, mock_agent_data):
    """Test successful agent creation"""
    # Setup mocks
    mock_db.agent.create.return_value = mock_agent_data
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        
        # Mock the deployment method to avoid actual deployment
        agent_service._deploy_agent = AsyncMock()
        
        result = await agent_service.create_agent(sample_agent_config)
        
        # Verify agent was created
        assert result == mock_agent_data
        mock_db.agent.create.assert_called_once()
        
        # Verify deployment was initiated
        agent_service._deploy_agent.assert_called_once_with(mock_agent_data)


@pytest.mark.asyncio
async def test_get_agent_success(mock_db, mock_agent_data):
    """Test successful agent retrieval"""
    # Setup mocks
    mock_db.agent.find_unique.return_value = mock_agent_data
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        result = await agent_service.get_agent("test-agent-id")
        
        assert result == mock_agent_data
        mock_db.agent.find_unique.assert_called_once_with(
            where={"id": "test-agent-id"},
            include={
                "workflows": True,
                "tools": True,
                "conversations": True
            }
        )


@pytest.mark.asyncio
async def test_get_agent_not_found(mock_db):
    """Test agent retrieval when agent doesn't exist"""
    # Setup mocks
    mock_db.agent.find_unique.return_value = None
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        result = await agent_service.get_agent("nonexistent-id")
        
        assert result is None


@pytest.mark.asyncio
async def test_list_agents_success(mock_db, mock_agent_data):
    """Test successful agent listing"""
    # Setup mocks
    mock_db.agent.find_many.return_value = [mock_agent_data]
    mock_db.agent.count.return_value = 1
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        agents, total = await agent_service.list_agents(page=1, size=20)
        
        assert agents == [mock_agent_data]
        assert total == 1
        
        mock_db.agent.find_many.assert_called_once_with(
            where={},
            skip=0,
            take=20,
            order={"createdAt": "desc"}
        )
        mock_db.agent.count.assert_called_once_with(where={})


@pytest.mark.asyncio
async def test_list_agents_with_status_filter(mock_db, mock_agent_data):
    """Test agent listing with status filter"""
    # Setup mocks
    mock_db.agent.find_many.return_value = [mock_agent_data]
    mock_db.agent.count.return_value = 1
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        agents, total = await agent_service.list_agents(
            page=1, 
            size=20, 
            status_filter=AgentStatus.CREATED
        )
        
        assert agents == [mock_agent_data]
        assert total == 1
        
        mock_db.agent.find_many.assert_called_once_with(
            where={"status": "CREATED"},
            skip=0,
            take=20,
            order={"createdAt": "desc"}
        )
        mock_db.agent.count.assert_called_once_with(where={"status": "CREATED"})


@pytest.mark.asyncio
async def test_update_agent_success(mock_db, sample_agent_config, mock_agent_data):
    """Test successful agent update"""
    # Setup mocks
    updated_agent_data = mock_agent_data
    updated_agent_data.name = "Updated Test Agent"
    
    mock_db.agent.find_unique.return_value = mock_agent_data
    mock_db.agent.update.return_value = updated_agent_data
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        
        # Mock the deployment method
        agent_service._deploy_agent = AsyncMock()
        
        updated_config = sample_agent_config.copy()
        updated_config.name = "Updated Test Agent"
        
        result = await agent_service.update_agent("test-agent-id", updated_config)
        
        assert result == updated_agent_data
        mock_db.agent.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_agent_not_found(mock_db, sample_agent_config):
    """Test agent update when agent doesn't exist"""
    # Setup mocks
    mock_db.agent.find_unique.return_value = None
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        result = await agent_service.update_agent("nonexistent-id", sample_agent_config)
        
        assert result is None


@pytest.mark.asyncio
async def test_delete_agent_success(mock_db, mock_agent_data):
    """Test successful agent deletion"""
    # Setup mocks
    mock_db.agent.find_unique.return_value = mock_agent_data
    mock_db.agent.delete.return_value = None
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        
        # Mock the undeployment method
        agent_service._undeploy_agent = AsyncMock()
        
        result = await agent_service.delete_agent("test-agent-id")
        
        assert result is True
        mock_db.agent.delete.assert_called_once_with(where={"id": "test-agent-id"})


@pytest.mark.asyncio
async def test_delete_agent_not_found(mock_db):
    """Test agent deletion when agent doesn't exist"""
    # Setup mocks
    mock_db.agent.find_unique.return_value = None
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        result = await agent_service.delete_agent("nonexistent-id")
        
        assert result is False


@pytest.mark.asyncio
async def test_get_agent_by_name_success(mock_db, mock_agent_data):
    """Test successful agent retrieval by name"""
    # Setup mocks
    mock_db.agent.find_first.return_value = mock_agent_data
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        result = await agent_service.get_agent_by_name("Test Agent")
        
        assert result == mock_agent_data
        mock_db.agent.find_first.assert_called_once_with(where={"name": "Test Agent"})


@pytest.mark.asyncio
async def test_search_agents_success(mock_db, mock_agent_data):
    """Test successful agent search"""
    # Setup mocks
    mock_db.agent.find_many.return_value = [mock_agent_data]
    mock_db.agent.count.return_value = 1
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        agents, total = await agent_service.search_agents("Test", page=1, size=20)
        
        assert agents == [mock_agent_data]
        assert total == 1
        
        expected_where = {
            "OR": [
                {"name": {"contains": "Test", "mode": "insensitive"}},
                {"description": {"contains": "Test", "mode": "insensitive"}}
            ]
        }
        
        mock_db.agent.find_many.assert_called_once_with(
            where=expected_where,
            skip=0,
            take=20,
            order={"updatedAt": "desc"}
        )
        mock_db.agent.count.assert_called_once_with(where=expected_where)


@pytest.mark.asyncio
async def test_can_delete_agent_success(mock_db):
    """Test can_delete_agent when agent can be deleted"""
    # Setup mocks - no active workflows or conversations
    mock_db.workflow.count.return_value = 0
    mock_db.conversationsession.count.return_value = 0
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        can_delete, reason = await agent_service.can_delete_agent("test-agent-id")
        
        assert can_delete is True
        assert reason is None


@pytest.mark.asyncio
async def test_can_delete_agent_with_active_workflows(mock_db):
    """Test can_delete_agent when agent has active workflows"""
    # Setup mocks - has active workflows
    mock_db.workflow.count.return_value = 2
    mock_db.conversationsession.count.return_value = 0
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        can_delete, reason = await agent_service.can_delete_agent("test-agent-id")
        
        assert can_delete is False
        assert reason == "Agent has 2 active workflow(s)"


@pytest.mark.asyncio
async def test_can_delete_agent_with_active_conversations(mock_db):
    """Test can_delete_agent when agent has active conversations"""
    # Setup mocks - has active conversations
    mock_db.workflow.count.return_value = 0
    mock_db.conversationsession.count.return_value = 1
    
    with patch('services.agent_management.services.agent_service.ADKClient'), \
         patch('services.agent_management.services.agent_service.VertexAIClient'):
        
        agent_service = AgentService(mock_db)
        can_delete, reason = await agent_service.can_delete_agent("test-agent-id")
        
        assert can_delete is False
        assert reason == "Agent has 1 active conversation(s)"