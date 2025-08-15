import pytest
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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