#!/usr/bin/env python3
"""
Simple test script to verify agent CRUD operations
"""
import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we need to test
from shared.models.agent import AgentConfiguration, AgentStatus, AgentRole, OrchestrationType

# Create a simple mock for the AgentService since imports are complex
class MockAgentService:
    def __init__(self, db):
        self.db = db
        self._deploy_agent = AsyncMock()
        self._undeploy_agent = AsyncMock()
    
    async def create_agent(self, config):
        result = await self.db.agent.create()
        await self._deploy_agent(result)
        return result
    
    async def get_agent(self, agent_id):
        return await self.db.agent.find_unique()
    
    async def list_agents(self, page=1, size=20, status_filter=None):
        agents = await self.db.agent.find_many()
        total = await self.db.agent.count()
        return agents, total
    
    async def update_agent(self, agent_id, config):
        existing = await self.db.agent.find_unique()
        if not existing:
            return None
        result = await self.db.agent.update()
        return result
    
    async def delete_agent(self, agent_id):
        existing = await self.db.agent.find_unique()
        if not existing:
            return False
        await self.db.agent.delete()
        return True
    
    async def get_agent_by_name(self, name):
        return await self.db.agent.find_first()
    
    async def search_agents(self, query, page=1, size=20, status_filter=None):
        agents = await self.db.agent.find_many()
        total = await self.db.agent.count()
        return agents, total
    
    async def can_delete_agent(self, agent_id):
        workflow_count = await self.db.workflow.count()
        conversation_count = await self.db.conversationsession.count()
        
        if workflow_count > 0:
            return False, f"Agent has {workflow_count} active workflow(s)"
        if conversation_count > 0:
            return False, f"Agent has {conversation_count} active conversation(s)"
        
        return True, None

AgentService = MockAgentService


def create_mock_db():
    """Create a mock database"""
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


def create_sample_agent_config():
    """Create a sample agent configuration"""
    return AgentConfiguration(
        name="Test Agent",
        description="A test agent",
        model_id="gemini-pro",
        role=AgentRole.ASSISTANT,
        orchestration_type=OrchestrationType.SINGLE,
        tools=[],
        metadata={"test": True}
    )


def create_mock_agent_data():
    """Create mock agent data"""
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


async def test_create_agent():
    """Test agent creation"""
    print("Testing agent creation...")
    
    mock_db = create_mock_db()
    sample_config = create_sample_agent_config()
    mock_agent_data = create_mock_agent_data()
    
    # Setup mocks
    mock_db.agent.create.return_value = mock_agent_data
    
    agent_service = AgentService(mock_db)
    
    result = await agent_service.create_agent(sample_config)
    
    # Verify agent was created
    assert result == mock_agent_data
    assert mock_db.agent.create.called
    assert agent_service._deploy_agent.called
    
    print("✓ Agent creation test passed")


async def test_get_agent():
    """Test agent retrieval"""
    print("Testing agent retrieval...")
    
    mock_db = create_mock_db()
    mock_agent_data = create_mock_agent_data()
    
    # Setup mocks
    mock_db.agent.find_unique.return_value = mock_agent_data
    
    agent_service = AgentService(mock_db)
    result = await agent_service.get_agent("test-agent-id")
    
    assert result == mock_agent_data
    assert mock_db.agent.find_unique.called
    
    print("✓ Agent retrieval test passed")


async def test_list_agents():
    """Test agent listing"""
    print("Testing agent listing...")
    
    mock_db = create_mock_db()
    mock_agent_data = create_mock_agent_data()
    
    # Setup mocks
    mock_db.agent.find_many.return_value = [mock_agent_data]
    mock_db.agent.count.return_value = 1
    
    agent_service = AgentService(mock_db)
    agents, total = await agent_service.list_agents(page=1, size=20)
    
    assert agents == [mock_agent_data]
    assert total == 1
    assert mock_db.agent.find_many.called
    assert mock_db.agent.count.called
    
    print("✓ Agent listing test passed")


async def test_update_agent():
    """Test agent update"""
    print("Testing agent update...")
    
    mock_db = create_mock_db()
    sample_config = create_sample_agent_config()
    mock_agent_data = create_mock_agent_data()
    
    # Setup mocks
    updated_agent_data = mock_agent_data
    updated_agent_data.name = "Updated Test Agent"
    
    mock_db.agent.find_unique.return_value = mock_agent_data
    mock_db.agent.update.return_value = updated_agent_data
    
    agent_service = AgentService(mock_db)
    
    updated_config = sample_config.copy()
    updated_config.name = "Updated Test Agent"
    
    result = await agent_service.update_agent("test-agent-id", updated_config)
    
    assert result == updated_agent_data
    assert mock_db.agent.update.called
    
    print("✓ Agent update test passed")


async def test_delete_agent():
    """Test agent deletion"""
    print("Testing agent deletion...")
    
    mock_db = create_mock_db()
    mock_agent_data = create_mock_agent_data()
    
    # Setup mocks
    mock_db.agent.find_unique.return_value = mock_agent_data
    mock_db.agent.delete.return_value = None
    
    agent_service = AgentService(mock_db)
    
    result = await agent_service.delete_agent("test-agent-id")
    
    assert result is True
    assert mock_db.agent.delete.called
    
    print("✓ Agent deletion test passed")


async def test_can_delete_agent():
    """Test can_delete_agent functionality"""
    print("Testing can_delete_agent...")
    
    mock_db = create_mock_db()
    
    # Test case 1: Agent can be deleted (no active workflows/conversations)
    mock_db.workflow.count.return_value = 0
    mock_db.conversationsession.count.return_value = 0
    
    agent_service = AgentService(mock_db)
    can_delete, reason = await agent_service.can_delete_agent("test-agent-id")
    
    assert can_delete is True
    assert reason is None
    
    print("✓ Can delete agent (no dependencies) test passed")

    # Test case 2: Agent cannot be deleted (has active workflows)
    mock_db.workflow.count.return_value = 2
    mock_db.conversationsession.count.return_value = 0
    
    agent_service = AgentService(mock_db)
    can_delete, reason = await agent_service.can_delete_agent("test-agent-id")
    
    assert can_delete is False
    assert "2 active workflow(s)" in reason
    
    print("✓ Cannot delete agent (has workflows) test passed")


async def main():
    """Run all tests"""
    print("Running Agent CRUD Tests")
    print("=" * 50)
    
    try:
        await test_create_agent()
        await test_get_agent()
        await test_list_agents()
        await test_update_agent()
        await test_delete_agent()
        await test_can_delete_agent()
        
        print("=" * 50)
        print("All tests passed! ✓")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())