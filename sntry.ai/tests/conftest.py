import pytest
import asyncio
import sys
import os
from httpx import AsyncClient
from prisma import Prisma
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services'))
sys.path.insert(0, os.path.join(project_root, 'services', 'agent-management'))

from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db():
    """Database fixture for tests"""
    db = MagicMock()
    
    # Mock agent operations
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
    
    yield db


@pytest.fixture
async def client():
    """HTTP client fixture for API tests"""
    # Mock the database and external services
    with patch('shared.database.get_db') as mock_get_db, \
         patch('services.agent_management.integrations.adk_client.ADKClient'), \
         patch('services.agent_management.integrations.vertex_ai_client.VertexAIClient'):
        
        # Setup mock database
        mock_db = MagicMock()
        mock_db.agent.create = AsyncMock()
        mock_db.agent.find_unique = AsyncMock()
        mock_db.agent.find_first = AsyncMock()
        mock_db.agent.find_many = AsyncMock()
        mock_db.agent.find_many_and_count = AsyncMock()
        mock_db.agent.update = AsyncMock()
        mock_db.agent.delete = AsyncMock()
        mock_db.agent.count = AsyncMock()
        mock_db.workflow.count = AsyncMock(return_value=0)
        mock_db.conversationsession.count = AsyncMock(return_value=0)
        
        # Mock the context manager
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def sample_agent_config():
    """Sample agent configuration for tests"""
    return {
        "name": "Test Agent",
        "description": "A test agent",
        "model_id": "gemini-pro",
        "role": "ASSISTANT",
        "orchestration_type": "SINGLE",
        "memory_config": {
            "type": "conversation",
            "max_history": 100,
            "persistence": True,
            "context_window": 4000
        },
        "tools": [],
        "metadata": {"test": True}
    }


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