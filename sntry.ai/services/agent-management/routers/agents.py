from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from shared.database import get_db
from shared.models.agent import (
    AgentCreateRequest, AgentUpdateRequest, AgentResponse, AgentListResponse,
    AgentStatus
)
from shared.models.base import PaginationParams, PaginatedResponse, ErrorResponse
from shared.utils.logging import get_logger
from ..services.agent_service import AgentService
import uuid

router = APIRouter()
logger = get_logger("agents-router")


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreateRequest):
    """Create a new AI agent
    
    Creates a new AI agent with the provided configuration. The agent will be
    automatically deployed to the Vertex AI Agent Engine.
    
    Args:
        request: Agent configuration including name, model, role, and other settings
        
    Returns:
        AgentResponse: Created agent details
        
    Raises:
        400: Invalid configuration or validation errors
        409: Agent with the same name already exists
        500: Internal server error during creation
    """
    request_id = str(uuid.uuid4())
    logger.info("Creating agent", request_id=request_id, name=request.configuration.name)
    
    try:
        async with get_db() as db:
            agent_service = AgentService(db)
            
            # Check if agent with same name exists
            existing_agent = await agent_service.get_agent_by_name(request.configuration.name)
            if existing_agent:
                logger.warning("Agent name already exists", request_id=request_id, name=request.configuration.name)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=ErrorResponse(
                        status=status.HTTP_409_CONFLICT,
                        error_code="AGENT_NAME_EXISTS",
                        message=f"Agent with name '{request.configuration.name}' already exists",
                        request_id=request_id
                    ).dict()
                )
            
            agent = await agent_service.create_agent(request.configuration)
            logger.info("Agent created successfully", request_id=request_id, agent_id=agent.id)
            return AgentResponse(agent=agent)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create agent", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AGENT_CREATION_FAILED",
                message="Failed to create agent",
                request_id=request_id
            ).dict()
        )


@router.get("/", response_model=PaginatedResponse)
async def list_agents(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[AgentStatus] = Query(None, description="Filter agents by status"),
    search: Optional[str] = Query(None, description="Search agents by name or description")
):
    """List all AI agents with optional filtering
    
    Retrieves a paginated list of AI agents with optional filtering by status
    and search functionality.
    
    Args:
        pagination: Pagination parameters (page, size)
        status_filter: Optional status filter (CREATED, DEPLOYING, DEPLOYED, FAILED, STOPPED)
        search: Optional search query for agent name or description
        
    Returns:
        PaginatedResponse: List of agents with pagination metadata
        
    Raises:
        500: Internal server error during retrieval
    """
    request_id = str(uuid.uuid4())
    logger.info("Listing agents", request_id=request_id, page=pagination.page, size=pagination.size)
    
    try:
        async with get_db() as db:
            agent_service = AgentService(db)
            
            if search:
                agents, total = await agent_service.search_agents(
                    query=search,
                    page=pagination.page,
                    size=pagination.size,
                    status_filter=status_filter
                )
            else:
                agents, total = await agent_service.list_agents(
                    page=pagination.page,
                    size=pagination.size,
                    status_filter=status_filter
                )
            
            logger.info("Agents listed successfully", request_id=request_id, count=len(agents), total=total)
            return PaginatedResponse.create(
                data=agents,
                page=pagination.page,
                size=pagination.size,
                total=total
            )
            
    except Exception as e:
        logger.error("Failed to list agents", request_id=request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AGENT_LIST_FAILED",
                message="Failed to retrieve agents",
                request_id=request_id
            ).dict()
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get details of a specific AI agent
    
    Retrieves detailed information about a specific agent including its
    configuration, status, deployment info, and related resources.
    
    Args:
        agent_id: Unique identifier of the agent
        
    Returns:
        AgentResponse: Agent details
        
    Raises:
        400: Invalid agent ID format
        404: Agent not found
        500: Internal server error during retrieval
    """
    request_id = str(uuid.uuid4())
    logger.info("Getting agent", request_id=request_id, agent_id=agent_id)
    
    # Validate agent_id format (should be UUID)
    try:
        uuid.UUID(agent_id)
    except ValueError:
        logger.warning("Invalid agent ID format", request_id=request_id, agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_AGENT_ID",
                message="Agent ID must be a valid UUID",
                request_id=request_id
            ).dict()
        )
    
    try:
        async with get_db() as db:
            agent_service = AgentService(db)
            agent = await agent_service.get_agent(agent_id)
            
            if not agent:
                logger.warning("Agent not found", request_id=request_id, agent_id=agent_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        status=status.HTTP_404_NOT_FOUND,
                        error_code="AGENT_NOT_FOUND",
                        message=f"Agent with ID '{agent_id}' not found",
                        request_id=request_id
                    ).dict()
                )
            
            logger.info("Agent retrieved successfully", request_id=request_id, agent_id=agent_id)
            return AgentResponse(agent=agent)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent", request_id=request_id, agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AGENT_RETRIEVAL_FAILED",
                message="Failed to retrieve agent",
                request_id=request_id
            ).dict()
        )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, request: AgentUpdateRequest):
    """Update an existing AI agent's configuration
    
    Updates the configuration of an existing agent. If the agent is currently
    deployed, it will be redeployed with the new configuration.
    
    Args:
        agent_id: Unique identifier of the agent
        request: Updated agent configuration
        
    Returns:
        AgentResponse: Updated agent details
        
    Raises:
        400: Invalid agent ID format or configuration
        404: Agent not found
        409: Configuration conflict (e.g., name already exists)
        500: Internal server error during update
    """
    request_id = str(uuid.uuid4())
    logger.info("Updating agent", request_id=request_id, agent_id=agent_id, name=request.configuration.name)
    
    # Validate agent_id format
    try:
        uuid.UUID(agent_id)
    except ValueError:
        logger.warning("Invalid agent ID format", request_id=request_id, agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_AGENT_ID",
                message="Agent ID must be a valid UUID",
                request_id=request_id
            ).dict()
        )
    
    try:
        async with get_db() as db:
            agent_service = AgentService(db)
            
            # Check if agent exists
            existing_agent = await agent_service.get_agent(agent_id)
            if not existing_agent:
                logger.warning("Agent not found for update", request_id=request_id, agent_id=agent_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        status=status.HTTP_404_NOT_FOUND,
                        error_code="AGENT_NOT_FOUND",
                        message=f"Agent with ID '{agent_id}' not found",
                        request_id=request_id
                    ).dict()
                )
            
            # Check if new name conflicts with existing agent (if name changed)
            if existing_agent.name != request.configuration.name:
                name_conflict = await agent_service.get_agent_by_name(request.configuration.name)
                if name_conflict and name_conflict.id != agent_id:
                    logger.warning("Agent name conflict during update", request_id=request_id, name=request.configuration.name)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=ErrorResponse(
                            status=status.HTTP_409_CONFLICT,
                            error_code="AGENT_NAME_EXISTS",
                            message=f"Agent with name '{request.configuration.name}' already exists",
                            request_id=request_id
                        ).dict()
                    )
            
            agent = await agent_service.update_agent(agent_id, request.configuration)
            logger.info("Agent updated successfully", request_id=request_id, agent_id=agent_id)
            return AgentResponse(agent=agent)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update agent", request_id=request_id, agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AGENT_UPDATE_FAILED",
                message="Failed to update agent",
                request_id=request_id
            ).dict()
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str):
    """Delete an AI agent instance
    
    Permanently deletes an AI agent. If the agent is currently deployed,
    it will be undeployed first. This action cannot be undone.
    
    Args:
        agent_id: Unique identifier of the agent
        
    Returns:
        204 No Content on successful deletion
        
    Raises:
        400: Invalid agent ID format
        404: Agent not found
        409: Agent cannot be deleted (e.g., has active workflows)
        500: Internal server error during deletion
    """
    request_id = str(uuid.uuid4())
    logger.info("Deleting agent", request_id=request_id, agent_id=agent_id)
    
    # Validate agent_id format
    try:
        uuid.UUID(agent_id)
    except ValueError:
        logger.warning("Invalid agent ID format", request_id=request_id, agent_id=agent_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_AGENT_ID",
                message="Agent ID must be a valid UUID",
                request_id=request_id
            ).dict()
        )
    
    try:
        async with get_db() as db:
            agent_service = AgentService(db)
            
            # Check if agent exists and can be deleted
            existing_agent = await agent_service.get_agent(agent_id)
            if not existing_agent:
                logger.warning("Agent not found for deletion", request_id=request_id, agent_id=agent_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        status=status.HTTP_404_NOT_FOUND,
                        error_code="AGENT_NOT_FOUND",
                        message=f"Agent with ID '{agent_id}' not found",
                        request_id=request_id
                    ).dict()
                )
            
            # Check for active workflows or conversations that prevent deletion
            can_delete, reason = await agent_service.can_delete_agent(agent_id)
            if not can_delete:
                logger.warning("Agent cannot be deleted", request_id=request_id, agent_id=agent_id, reason=reason)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=ErrorResponse(
                        status=status.HTTP_409_CONFLICT,
                        error_code="AGENT_DELETION_BLOCKED",
                        message=f"Agent cannot be deleted: {reason}",
                        request_id=request_id
                    ).dict()
                )
            
            success = await agent_service.delete_agent(agent_id)
            if success:
                logger.info("Agent deleted successfully", request_id=request_id, agent_id=agent_id)
            else:
                # This shouldn't happen given our checks above, but handle it
                logger.error("Agent deletion failed unexpectedly", request_id=request_id, agent_id=agent_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=ErrorResponse(
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        error_code="AGENT_DELETION_FAILED",
                        message="Failed to delete agent",
                        request_id=request_id
                    ).dict()
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete agent", request_id=request_id, agent_id=agent_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="AGENT_DELETION_FAILED",
                message="Failed to delete agent",
                request_id=request_id
            ).dict()
        )