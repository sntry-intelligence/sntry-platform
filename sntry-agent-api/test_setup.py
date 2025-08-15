#!/usr/bin/env python3
"""
Test script to verify the AI Agent Framework setup
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(__file__))

def test_imports():
    """Test that all core components can be imported"""
    try:
        # Test shared models
        from shared.models.base import AgentConfig, TrainingJob, Tool, Thread
        print("✅ Shared models imported successfully")
        
        # Test shared utilities
        from shared.utils.logging import setup_logging
        from shared.utils.redis_client import RedisClient
        print("✅ Shared utilities imported successfully")
        
        # Test base service
        from shared.interfaces.base_service import BaseService
        print("✅ Base service interface imported successfully")
        
        # Test FastAPI and other dependencies
        import fastapi
        import uvicorn
        import sqlalchemy
        import redis
        import pydantic
        print("✅ All dependencies imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_models():
    """Test that models can be instantiated"""
    try:
        from shared.models.base import AgentConfig, AgentType, MemoryConfig
        
        # Create a sample agent config
        memory_config = MemoryConfig(max_context_length=8192)
        agent_config = AgentConfig(
            name="test-agent",
            type=AgentType.PROMPT_BASED,
            model_id="gpt-4",
            capabilities=["text-generation", "reasoning"],
            memory_config=memory_config
        )
        
        print(f"✅ Created agent config: {agent_config.name}")
        print(f"   - Type: {agent_config.type}")
        print(f"   - Model: {agent_config.model_id}")
        print(f"   - Memory: {agent_config.memory_config.max_context_length} tokens")
        
        return True
    except Exception as e:
        print(f"❌ Model creation error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing AI Agent Framework Setup")
    print("=" * 50)
    
    # Test Python version
    print(f"Python version: {sys.version}")
    print(f"Virtual environment: {sys.prefix}")
    print()
    
    # Run tests
    tests = [
        ("Import Tests", test_imports),
        ("Model Tests", test_models),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    print("=" * 50)
    if all(results):
        print("🎉 All tests passed! Virtual environment is ready.")
        print("\nNext steps:")
        print("1. Start infrastructure: docker-compose up -d postgres redis")
        print("2. Run services: ./scripts/start-dev.sh")
        print("3. Test endpoints: curl http://localhost:8001/health")
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())