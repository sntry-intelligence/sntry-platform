#!/usr/bin/env python3
"""
Simple test runner to verify our models and repositories work
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_model_imports():
    """Test that all models can be imported successfully"""
    try:
        from shared.models import (
            # Agent models
            Agent, AgentStatus, AgentRole, OrchestrationType,
            AgentConfiguration, DeploymentInfo, MemoryConfiguration,
            AgentCreateRequest, AgentUpdateRequest,
            
            # Workflow models
            Workflow, WorkflowType, WorkflowStatus, ExecutionStatus,
            WorkflowDefinition, WorkflowStep, WorkflowExecution,
            WorkflowCreateRequest, WorkflowExecutionRequest,
            
            # Tool models
            Tool, ToolStatus, ParameterType,
            ToolDefinition, FunctionSignature, FunctionParameter,
            ConnectionConfig, SecurityPolicy, InvocationContext,
            ToolCreateRequest, ToolInvocationRequest,
            
            # Conversation models
            ConversationSession, SessionStatus, MessageRole,
            Message, ConversationContext, ToolCall,
            ConversationSessionCreateRequest, MessageCreateRequest,
            
            # Vector store models
            VectorStore, VectorStoreType, VectorStoreStatus,
            VectorStoreConfiguration, IndexingConfig, EmbeddingModelConfig,
            VectorStoreCreateRequest, VectorQuery,
            
            # Base models
            BaseResponse, ErrorResponse, PaginationParams
        )
        print("✅ All models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False


def test_repository_imports():
    """Test that all repositories can be imported successfully"""
    try:
        from shared.repositories import (
            BaseRepository, CacheableRepository, AuditableRepository,
            AgentRepository, WorkflowRepository, WorkflowExecutionRepository,
            ToolRepository, ToolInvocationRepository,
            ConversationSessionRepository, MessageRepository,
            VectorStoreRepository, EmbeddingRepository
        )
        print("✅ All repositories imported successfully")
        return True
    except Exception as e:
        print(f"❌ Repository import failed: {e}")
        return False


def test_database_imports():
    """Test that database utilities can be imported successfully"""
    try:
        from shared.database import (
            CacheManager, RateLimiter, SessionManager,
            health_check, DatabaseManager
        )
        print("✅ All database utilities imported successfully")
        return True
    except Exception as e:
        print(f"❌ Database utilities import failed: {e}")
        return False


def test_agent_configuration_creation():
    """Test AgentConfiguration model creation"""
    try:
        from shared.models import AgentConfiguration, AgentRole, OrchestrationType
        
        config = AgentConfiguration(
            name="Test Agent",
            description="A test agent",
            model_id="gpt-4",
            role=AgentRole.ASSISTANT,
            orchestration_type=OrchestrationType.SINGLE
        )
        
        assert config.name == "Test Agent"
        assert config.role == AgentRole.ASSISTANT
        assert config.orchestration_type == OrchestrationType.SINGLE
        assert config.tools == []
        assert config.metadata == {}
        
        print("✅ AgentConfiguration creation test passed")
        return True
    except Exception as e:
        print(f"❌ AgentConfiguration creation test failed: {e}")
        return False


def test_workflow_definition_creation():
    """Test WorkflowDefinition model creation"""
    try:
        from shared.models import WorkflowDefinition, WorkflowStep, WorkflowType
        
        steps = [
            WorkflowStep(id="step-1", name="Step 1", action="action1"),
            WorkflowStep(id="step-2", name="Step 2", action="action2")
        ]
        
        definition = WorkflowDefinition(
            type=WorkflowType.SEQUENTIAL,
            steps=steps
        )
        
        assert definition.type == WorkflowType.SEQUENTIAL
        assert len(definition.steps) == 2
        assert definition.agent_roles == []
        
        print("✅ WorkflowDefinition creation test passed")
        return True
    except Exception as e:
        print(f"❌ WorkflowDefinition creation test failed: {e}")
        return False


def test_tool_definition_creation():
    """Test ToolDefinition model creation"""
    try:
        from shared.models import (
            ToolDefinition, FunctionSignature, ConnectionConfig, SecurityPolicy
        )
        
        signature = FunctionSignature(
            name="test_tool",
            description="A test tool",
            parameters=[]
        )
        
        connection = ConnectionConfig(
            type="http",
            endpoint="https://api.test.com"
        )
        
        definition = ToolDefinition(
            name="Test Tool",
            description="A tool for testing",
            function_signature=signature,
            connection_details=connection
        )
        
        assert definition.name == "Test Tool"
        assert definition.function_signature.name == "test_tool"
        assert isinstance(definition.security_policy, SecurityPolicy)
        
        print("✅ ToolDefinition creation test passed")
        return True
    except Exception as e:
        print(f"❌ ToolDefinition creation test failed: {e}")
        return False


def test_vector_store_configuration():
    """Test VectorStoreConfiguration model creation"""
    try:
        from shared.models import (
            VectorStoreConfiguration, VectorStoreType,
            IndexingConfig, EmbeddingModelConfig
        )
        
        indexing = IndexingConfig(dimension=1536)
        embedding = EmbeddingModelConfig(
            model_id="test-model",
            provider="test"
        )
        
        config = VectorStoreConfiguration(
            type=VectorStoreType.PINECONE,
            connection_details={"api_key": "secret"},
            indexing_parameters=indexing,
            embedding_model=embedding
        )
        
        assert config.type == VectorStoreType.PINECONE
        assert config.indexing_parameters.dimension == 1536
        assert config.embedding_model.model_id == "test-model"
        
        print("✅ VectorStoreConfiguration creation test passed")
        return True
    except Exception as e:
        print(f"❌ VectorStoreConfiguration creation test failed: {e}")
        return False


def test_pagination_params():
    """Test PaginationParams model"""
    try:
        from shared.models import PaginationParams
        
        # Test default values
        pagination = PaginationParams()
        assert pagination.page == 1
        assert pagination.size == 20
        
        # Test custom values
        pagination = PaginationParams(page=2, size=50)
        assert pagination.page == 2
        assert pagination.size == 50
        
        print("✅ PaginationParams test passed")
        return True
    except Exception as e:
        print(f"❌ PaginationParams test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Running sntry.ai data models and repositories tests...\n")
    
    tests = [
        test_model_imports,
        test_repository_imports,
        test_database_imports,
        test_agent_configuration_creation,
        test_workflow_definition_creation,
        test_tool_definition_creation,
        test_vector_store_configuration,
        test_pagination_params,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)