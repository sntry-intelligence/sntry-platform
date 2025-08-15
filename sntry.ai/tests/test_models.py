"""
Unit tests for Pydantic models
"""

import pytest
from datetime import datetime
from typing import Dict, Any

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


class TestAgentModels:
    """Test agent-related models"""
    
    def test_agent_configuration_creation(self):
        """Test AgentConfiguration model creation"""
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
        assert isinstance(config.memory_config, MemoryConfiguration)
        assert config.tools == []
        assert config.metadata == {}
    
    def test_agent_configuration_validation(self):
        """Test AgentConfiguration validation"""
        # Test name length validation
        with pytest.raises(ValueError):
            AgentConfiguration(
                name="",  # Empty name should fail
                model_id="gpt-4"
            )
        
        with pytest.raises(ValueError):
            AgentConfiguration(
                name="x" * 101,  # Too long name should fail
                model_id="gpt-4"
            )
    
    def test_memory_configuration_defaults(self):
        """Test MemoryConfiguration default values"""
        config = MemoryConfiguration()
        
        assert config.type == "conversation"
        assert config.max_history == 100
        assert config.persistence is True
        assert config.context_window == 4000
    
    def test_agent_create_request(self):
        """Test AgentCreateRequest model"""
        config = AgentConfiguration(
            name="Test Agent",
            model_id="gpt-4"
        )
        
        request = AgentCreateRequest(configuration=config)
        assert request.configuration.name == "Test Agent"
    
    def test_deployment_info(self):
        """Test DeploymentInfo model"""
        deployment = DeploymentInfo(
            vertex_ai_endpoint="https://vertex-ai.googleapis.com/endpoint",
            deployment_id="deployment-123",
            resource_pool="default-pool"
        )
        
        assert deployment.vertex_ai_endpoint is not None
        assert deployment.deployment_id == "deployment-123"
        assert deployment.scaling_config == {}


class TestWorkflowModels:
    """Test workflow-related models"""
    
    def test_workflow_step_creation(self):
        """Test WorkflowStep model creation"""
        step = WorkflowStep(
            id="step-1",
            name="Initial Step",
            action="process_input",
            parameters={"param1": "value1"},
            dependencies=["step-0"],
            timeout=30
        )
        
        assert step.id == "step-1"
        assert step.name == "Initial Step"
        assert step.action == "process_input"
        assert step.parameters == {"param1": "value1"}
        assert step.dependencies == ["step-0"]
        assert step.timeout == 30
    
    def test_workflow_definition(self):
        """Test WorkflowDefinition model"""
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
        assert isinstance(definition.error_handling.retry_attempts, int)
    
    def test_workflow_create_request(self):
        """Test WorkflowCreateRequest validation"""
        definition = WorkflowDefinition(
            type=WorkflowType.PARALLEL,
            steps=[WorkflowStep(id="1", name="Test", action="test")]
        )
        
        request = WorkflowCreateRequest(
            name="Test Workflow",
            description="A test workflow",
            definition=definition
        )
        
        assert request.name == "Test Workflow"
        assert request.definition.type == WorkflowType.PARALLEL
        
        # Test name validation
        with pytest.raises(ValueError):
            WorkflowCreateRequest(
                name="",  # Empty name should fail
                definition=definition
            )


class TestToolModels:
    """Test tool-related models"""
    
    def test_function_parameter(self):
        """Test FunctionParameter model"""
        param = FunctionParameter(
            name="input_text",
            type=ParameterType.STRING,
            description="Input text to process",
            required=True,
            default=None
        )
        
        assert param.name == "input_text"
        assert param.type == ParameterType.STRING
        assert param.required is True
        assert param.default is None
    
    def test_function_signature(self):
        """Test FunctionSignature model"""
        params = [
            FunctionParameter(
                name="text",
                type=ParameterType.STRING,
                description="Text to analyze"
            )
        ]
        
        signature = FunctionSignature(
            name="analyze_text",
            description="Analyze text content",
            parameters=params,
            return_type="object"
        )
        
        assert signature.name == "analyze_text"
        assert len(signature.parameters) == 1
        assert signature.return_type == "object"
    
    def test_connection_config(self):
        """Test ConnectionConfig model"""
        config = ConnectionConfig(
            type="http",
            endpoint="https://api.example.com",
            authentication={"type": "bearer", "token": "secret"},
            timeout=30
        )
        
        assert config.type == "http"
        assert config.endpoint == "https://api.example.com"
        assert config.timeout == 30
        assert config.headers == {}
    
    def test_security_policy(self):
        """Test SecurityPolicy model"""
        policy = SecurityPolicy(
            allowed_users=["user1", "user2"],
            allowed_roles=["admin"],
            rate_limit=100,
            require_approval=True,
            audit_logging=True
        )
        
        assert policy.allowed_users == ["user1", "user2"]
        assert policy.require_approval is True
        assert policy.data_classification == "internal"
    
    def test_tool_definition(self):
        """Test ToolDefinition model"""
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


class TestConversationModels:
    """Test conversation-related models"""
    
    def test_conversation_context(self):
        """Test ConversationContext model"""
        context = ConversationContext(
            user_preferences={"theme": "dark"},
            conversation_summary="Discussion about AI",
            key_entities=["AI", "machine learning"],
            topics=["technology", "automation"],
            sentiment="positive",
            language="en"
        )
        
        assert context.user_preferences == {"theme": "dark"}
        assert context.language == "en"
        assert "AI" in context.key_entities
    
    def test_tool_call(self):
        """Test ToolCall model"""
        tool_call = ToolCall(
            id="call-123",
            name="search_web",
            parameters={"query": "AI news"},
            result={"status": "success", "data": []}
        )
        
        assert tool_call.id == "call-123"
        assert tool_call.name == "search_web"
        assert tool_call.parameters["query"] == "AI news"
    
    def test_message_create_request(self):
        """Test MessageCreateRequest validation"""
        request = MessageCreateRequest(
            role=MessageRole.USER,
            content="Hello, how are you?",
            metadata={"timestamp": "2024-01-01T00:00:00Z"}
        )
        
        assert request.role == MessageRole.USER
        assert request.content == "Hello, how are you?"
        
        # Test content validation
        with pytest.raises(ValueError):
            MessageCreateRequest(
                role=MessageRole.USER,
                content="",  # Empty content should fail
            )
    
    def test_conversation_session_create_request(self):
        """Test ConversationSessionCreateRequest"""
        context = ConversationContext(language="es")
        
        request = ConversationSessionCreateRequest(
            user_id="user-123",
            context=context,
            metadata={"source": "web"}
        )
        
        assert request.user_id == "user-123"
        assert request.context.language == "es"
        assert request.metadata["source"] == "web"


class TestVectorStoreModels:
    """Test vector store-related models"""
    
    def test_indexing_config(self):
        """Test IndexingConfig model"""
        config = IndexingConfig(
            dimension=1536,
            metric="cosine",
            index_type="hnsw",
            parameters={"ef_construction": 200}
        )
        
        assert config.dimension == 1536
        assert config.metric == "cosine"
        assert config.index_type == "hnsw"
        assert config.parameters["ef_construction"] == 200
    
    def test_embedding_model_config(self):
        """Test EmbeddingModelConfig model"""
        config = EmbeddingModelConfig(
            model_id="text-embedding-ada-002",
            provider="openai",
            parameters={"batch_size": 100},
            max_batch_size=1000
        )
        
        assert config.model_id == "text-embedding-ada-002"
        assert config.provider == "openai"
        assert config.max_batch_size == 1000
    
    def test_vector_store_configuration(self):
        """Test VectorStoreConfiguration model"""
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
    
    def test_vector_query(self):
        """Test VectorQuery model"""
        query = VectorQuery(
            query_text="What is machine learning?",
            top_k=5,
            filters=[],
            include_metadata=True,
            include_content=True
        )
        
        assert query.query_text == "What is machine learning?"
        assert query.top_k == 5
        assert query.include_metadata is True
        
        # Test top_k validation
        with pytest.raises(ValueError):
            VectorQuery(query_text="test", top_k=0)  # Should be >= 1
        
        with pytest.raises(ValueError):
            VectorQuery(query_text="test", top_k=101)  # Should be <= 100


class TestBaseModels:
    """Test base models"""
    
    def test_base_response(self):
        """Test BaseResponse model"""
        response = BaseResponse(
            success=True,
            message="Operation completed successfully"
        )
        
        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert isinstance(response.timestamp, datetime)
    
    def test_error_response(self):
        """Test ErrorResponse model"""
        error = ErrorResponse(
            status=400,
            error_code="VALIDATION_ERROR",
            message="Invalid input provided",
            details={"field": "name", "issue": "required"},
            request_id="req-123"
        )
        
        assert error.status == 400
        assert error.error_code == "VALIDATION_ERROR"
        assert error.details["field"] == "name"
        assert error.request_id == "req-123"
    
    def test_pagination_params(self):
        """Test PaginationParams model"""
        pagination = PaginationParams(page=2, size=50)
        
        assert pagination.page == 2
        assert pagination.size == 50
        
        # Test validation
        with pytest.raises(ValueError):
            PaginationParams(page=0)  # Should be >= 1
        
        with pytest.raises(ValueError):
            PaginationParams(size=101)  # Should be <= 100
    
    def test_pagination_params_defaults(self):
        """Test PaginationParams default values"""
        pagination = PaginationParams()
        
        assert pagination.page == 1
        assert pagination.size == 20


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_agent_configuration_json(self):
        """Test AgentConfiguration JSON serialization"""
        config = AgentConfiguration(
            name="Test Agent",
            model_id="gpt-4",
            tools=["tool1", "tool2"]
        )
        
        # Test serialization
        json_data = config.dict()
        assert json_data["name"] == "Test Agent"
        assert json_data["tools"] == ["tool1", "tool2"]
        
        # Test deserialization
        restored_config = AgentConfiguration(**json_data)
        assert restored_config.name == config.name
        assert restored_config.tools == config.tools
    
    def test_workflow_definition_json(self):
        """Test WorkflowDefinition JSON serialization"""
        steps = [
            WorkflowStep(id="1", name="Step 1", action="action1"),
            WorkflowStep(id="2", name="Step 2", action="action2")
        ]
        
        definition = WorkflowDefinition(
            type=WorkflowType.SEQUENTIAL,
            steps=steps
        )
        
        # Test serialization
        json_data = definition.dict()
        assert json_data["type"] == "SEQUENTIAL"
        assert len(json_data["steps"]) == 2
        
        # Test deserialization
        restored_definition = WorkflowDefinition(**json_data)
        assert restored_definition.type == WorkflowType.SEQUENTIAL
        assert len(restored_definition.steps) == 2