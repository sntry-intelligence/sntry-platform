import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_create_agent_success(client: AsyncClient, sample_agent_config):
    """Test successful agent creation"""
    response = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "agent" in data
    assert data["agent"]["name"] == sample_agent_config["name"]
    assert data["agent"]["status"] == "CREATED"
    assert "id" in data["agent"]


@pytest.mark.asyncio
async def test_create_agent_invalid_config(client: AsyncClient):
    """Test agent creation with invalid configuration"""
    invalid_config = {
        "name": "",  # Empty name should fail validation
        "model_id": "gemini-pro"
    }
    
    response = await client.post(
        "/v1/agents/",
        json={"configuration": invalid_config}
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(client: AsyncClient, sample_agent_config):
    """Test agent creation with duplicate name"""
    # Create first agent
    response1 = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    assert response1.status_code == 201
    
    # Try to create second agent with same name
    response2 = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    
    assert response2.status_code == 409
    data = response2.json()
    assert data["detail"]["error_code"] == "AGENT_NAME_EXISTS"


@pytest.mark.asyncio
async def test_list_agents_empty(client: AsyncClient):
    """Test listing agents when none exist"""
    response = await client.get("/v1/agents/")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["data"] == []
    assert data["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_list_agents_with_pagination(client: AsyncClient, sample_agent_config):
    """Test listing agents with pagination"""
    # Create multiple agents
    for i in range(5):
        config = sample_agent_config.copy()
        config["name"] = f"Test Agent {i}"
        await client.post("/v1/agents/", json={"configuration": config})
    
    # Test pagination
    response = await client.get("/v1/agents/?page=1&size=2")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["size"] == 2
    assert data["pagination"]["has_next"] is True


@pytest.mark.asyncio
async def test_list_agents_with_status_filter(client: AsyncClient, sample_agent_config):
    """Test listing agents with status filter"""
    # Create an agent
    response = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    assert response.status_code == 201
    
    # List agents with CREATED status
    response = await client.get("/v1/agents/?status_filter=CREATED")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1
    for agent in data["data"]:
        assert agent["status"] == "CREATED"


@pytest.mark.asyncio
async def test_list_agents_with_search(client: AsyncClient, sample_agent_config):
    """Test listing agents with search"""
    # Create agents with different names
    config1 = sample_agent_config.copy()
    config1["name"] = "Search Test Agent"
    await client.post("/v1/agents/", json={"configuration": config1})
    
    config2 = sample_agent_config.copy()
    config2["name"] = "Another Agent"
    await client.post("/v1/agents/", json={"configuration": config2})
    
    # Search for specific agent
    response = await client.get("/v1/agents/?search=Search")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert "Search" in data["data"][0]["name"]


@pytest.mark.asyncio
async def test_get_agent_success(client: AsyncClient, sample_agent_config):
    """Test successful agent retrieval"""
    # Create an agent
    create_response = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    agent_id = create_response.json()["agent"]["id"]
    
    # Get the agent
    response = await client.get(f"/v1/agents/{agent_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["agent"]["id"] == agent_id
    assert data["agent"]["name"] == sample_agent_config["name"]


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient):
    """Test getting non-existent agent"""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/v1/agents/{fake_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error_code"] == "AGENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_agent_invalid_id(client: AsyncClient):
    """Test getting agent with invalid ID format"""
    response = await client.get("/v1/agents/invalid-id")
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == "INVALID_AGENT_ID"


@pytest.mark.asyncio
async def test_update_agent_success(client: AsyncClient, sample_agent_config):
    """Test successful agent update"""
    # Create an agent
    create_response = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    agent_id = create_response.json()["agent"]["id"]
    
    # Update the agent
    updated_config = sample_agent_config.copy()
    updated_config["name"] = "Updated Test Agent"
    updated_config["description"] = "Updated description"
    
    response = await client.put(
        f"/v1/agents/{agent_id}",
        json={"configuration": updated_config}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["agent"]["name"] == "Updated Test Agent"
    assert data["agent"]["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_agent_not_found(client: AsyncClient, sample_agent_config):
    """Test updating non-existent agent"""
    fake_id = str(uuid.uuid4())
    response = await client.put(
        f"/v1/agents/{fake_id}",
        json={"configuration": sample_agent_config}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error_code"] == "AGENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_agent_invalid_id(client: AsyncClient, sample_agent_config):
    """Test updating agent with invalid ID format"""
    response = await client.put(
        "/v1/agents/invalid-id",
        json={"configuration": sample_agent_config}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == "INVALID_AGENT_ID"


@pytest.mark.asyncio
async def test_update_agent_name_conflict(client: AsyncClient, sample_agent_config):
    """Test updating agent with conflicting name"""
    # Create two agents
    config1 = sample_agent_config.copy()
    config1["name"] = "Agent 1"
    response1 = await client.post("/v1/agents/", json={"configuration": config1})
    
    config2 = sample_agent_config.copy()
    config2["name"] = "Agent 2"
    response2 = await client.post("/v1/agents/", json={"configuration": config2})
    
    agent2_id = response2.json()["agent"]["id"]
    
    # Try to update agent 2 with agent 1's name
    config2["name"] = "Agent 1"
    response = await client.put(
        f"/v1/agents/{agent2_id}",
        json={"configuration": config2}
    )
    
    assert response.status_code == 409
    data = response.json()
    assert data["detail"]["error_code"] == "AGENT_NAME_EXISTS"


@pytest.mark.asyncio
async def test_delete_agent_success(client: AsyncClient, sample_agent_config):
    """Test successful agent deletion"""
    # Create an agent
    create_response = await client.post(
        "/v1/agents/",
        json={"configuration": sample_agent_config}
    )
    agent_id = create_response.json()["agent"]["id"]
    
    # Delete the agent
    response = await client.delete(f"/v1/agents/{agent_id}")
    
    assert response.status_code == 204
    
    # Verify agent is deleted
    get_response = await client.get(f"/v1/agents/{agent_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_agent_not_found(client: AsyncClient):
    """Test deleting non-existent agent"""
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"/v1/agents/{fake_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error_code"] == "AGENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_agent_invalid_id(client: AsyncClient):
    """Test deleting agent with invalid ID format"""
    response = await client.delete("/v1/agents/invalid-id")
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == "INVALID_AGENT_ID"


@pytest.mark.asyncio
async def test_delete_agent_with_active_workflows(client: AsyncClient, sample_agent_config):
    """Test deleting agent with active workflows (should fail)"""
    # This test would require setting up workflows, which is part of task 4.2
    # For now, we'll mock the service method
    with patch('services.agent_service.AgentService.can_delete_agent') as mock_can_delete:
        mock_can_delete.return_value = (False, "Agent has 1 active workflow(s)")
        
        # Create an agent
        create_response = await client.post(
            "/v1/agents/",
            json={"configuration": sample_agent_config}
        )
        agent_id = create_response.json()["agent"]["id"]
        
        # Try to delete the agent
        response = await client.delete(f"/v1/agents/{agent_id}")
        
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["error_code"] == "AGENT_DELETION_BLOCKED"


@pytest.mark.asyncio
async def test_agent_crud_validation_errors(client: AsyncClient):
    """Test various validation errors in agent CRUD operations"""
    # Test missing required fields
    response = await client.post(
        "/v1/agents/",
        json={"configuration": {}}
    )
    assert response.status_code == 422
    
    # Test invalid enum values
    invalid_config = {
        "name": "Test Agent",
        "model_id": "gemini-pro",
        "role": "INVALID_ROLE",
        "orchestration_type": "SINGLE"
    }
    response = await client.post(
        "/v1/agents/",
        json={"configuration": invalid_config}
    )
    assert response.status_code == 422
    
    # Test name too long
    long_name_config = {
        "name": "x" * 101,  # Exceeds max length
        "model_id": "gemini-pro",
        "role": "ASSISTANT",
        "orchestration_type": "SINGLE"
    }
    response = await client.post(
        "/v1/agents/",
        json={"configuration": long_name_config}
    )
    assert response.status_code == 422