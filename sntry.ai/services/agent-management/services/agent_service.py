from typing import List, Optional, Tuple
from prisma import Prisma
from prisma.models import Agent
from shared.models.agent import AgentConfiguration, AgentStatus
from shared.utils.logging import get_logger
from ..integrations.adk_client import ADKClient
from ..integrations.vertex_ai_client import VertexAIClient

logger = get_logger("agent-service")


class AgentService:
    """Service for managing AI agents"""
    
    def __init__(self, db: Prisma):
        self.db = db
        self.adk_client = ADKClient()
        self.vertex_ai_client = VertexAIClient()
    
    async def create_agent(self, config: AgentConfiguration) -> Agent:
        """Create a new AI agent"""
        try:
            # Create agent in database
            agent = await self.db.agent.create(
                data={
                    "name": config.name,
                    "description": config.description,
                    "modelId": config.model_id,
                    "role": config.role.value,
                    "orchestrationType": config.orchestration_type.value,
                    "status": AgentStatus.CREATED.value,
                    "configuration": config.dict(),
                    "metadata": config.metadata
                }
            )
            
            logger.info("Agent created", agent_id=agent.id, name=config.name)
            
            # Deploy agent using ADK and Vertex AI (async task)
            await self._deploy_agent(agent)
            
            return agent
            
        except Exception as e:
            logger.error("Failed to create agent", error=str(e), name=config.name)
            raise
    
    async def list_agents(
        self, 
        page: int = 1, 
        size: int = 20, 
        status_filter: Optional[AgentStatus] = None
    ) -> Tuple[List[Agent], int]:
        """List agents with pagination and optional status filtering"""
        try:
            skip = (page - 1) * size
            where_clause = {}
            
            if status_filter:
                where_clause["status"] = status_filter.value
            
            agents = await self.db.agent.find_many(
                where=where_clause,
                skip=skip,
                take=size,
                order={"createdAt": "desc"}
            )
            
            total = await self.db.agent.count(where=where_clause)
            
            return agents, total
            
        except Exception as e:
            logger.error("Failed to list agents", error=str(e))
            raise
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            agent = await self.db.agent.find_unique(
                where={"id": agent_id},
                include={
                    "workflows": True,
                    "tools": True,
                    "conversations": True
                }
            )
            
            return agent
            
        except Exception as e:
            logger.error("Failed to get agent", error=str(e), agent_id=agent_id)
            raise
    
    async def update_agent(self, agent_id: str, config: AgentConfiguration) -> Optional[Agent]:
        """Update agent configuration"""
        try:
            # Check if agent exists
            existing_agent = await self.db.agent.find_unique(where={"id": agent_id})
            if not existing_agent:
                return None
            
            # Update agent
            agent = await self.db.agent.update(
                where={"id": agent_id},
                data={
                    "name": config.name,
                    "description": config.description,
                    "modelId": config.model_id,
                    "role": config.role.value,
                    "orchestrationType": config.orchestration_type.value,
                    "configuration": config.dict(),
                    "metadata": config.metadata
                }
            )
            
            logger.info("Agent updated", agent_id=agent_id, name=config.name)
            
            # Redeploy agent if needed
            if existing_agent.status == AgentStatus.DEPLOYED.value:
                await self._deploy_agent(agent)
            
            return agent
            
        except Exception as e:
            logger.error("Failed to update agent", error=str(e), agent_id=agent_id)
            raise
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete agent"""
        try:
            # Check if agent exists
            existing_agent = await self.db.agent.find_unique(where={"id": agent_id})
            if not existing_agent:
                return False
            
            # Undeploy agent if deployed
            if existing_agent.status == AgentStatus.DEPLOYED.value:
                await self._undeploy_agent(existing_agent)
            
            # Delete agent
            await self.db.agent.delete(where={"id": agent_id})
            
            logger.info("Agent deleted", agent_id=agent_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete agent", error=str(e), agent_id=agent_id)
            raise
    
    async def _deploy_agent(self, agent: Agent):
        """Deploy agent using ADK and Vertex AI"""
        try:
            # Update status to deploying
            await self.db.agent.update(
                where={"id": agent.id},
                data={"status": AgentStatus.DEPLOYING.value}
            )
            
            # Create agent using ADK
            adk_agent = await self.adk_client.create_agent(agent.configuration)
            
            # Deploy to Vertex AI Agent Engine
            deployment_info = await self.vertex_ai_client.deploy_agent(
                agent_id=agent.id,
                adk_agent=adk_agent
            )
            
            # Update agent with deployment info
            await self.db.agent.update(
                where={"id": agent.id},
                data={
                    "status": AgentStatus.DEPLOYED.value,
                    "deploymentInfo": deployment_info
                }
            )
            
            logger.info("Agent deployed successfully", agent_id=agent.id)
            
        except Exception as e:
            # Update status to failed
            await self.db.agent.update(
                where={"id": agent.id},
                data={"status": AgentStatus.FAILED.value}
            )
            
            logger.error("Failed to deploy agent", error=str(e), agent_id=agent.id)
            raise
    
    async def _undeploy_agent(self, agent: Agent):
        """Undeploy agent from Vertex AI"""
        try:
            if agent.deploymentInfo:
                await self.vertex_ai_client.undeploy_agent(agent.deploymentInfo)
            
            logger.info("Agent undeployed", agent_id=agent.id)
            
        except Exception as e:
            logger.error("Failed to undeploy agent", error=str(e), agent_id=agent.id)
            # Don't raise - allow deletion to continue
    
    async def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        try:
            agent = await self.db.agent.find_first(where={"name": name})
            return agent
        except Exception as e:
            logger.error("Failed to get agent by name", error=str(e), name=name)
            raise
    
    async def search_agents(
        self, 
        query: str, 
        page: int = 1, 
        size: int = 20,
        status_filter: Optional[AgentStatus] = None
    ) -> Tuple[List[Agent], int]:
        """Search agents by name or description"""
        try:
            skip = (page - 1) * size
            where_clause = {
                "OR": [
                    {"name": {"contains": query, "mode": "insensitive"}},
                    {"description": {"contains": query, "mode": "insensitive"}}
                ]
            }
            
            if status_filter:
                where_clause["status"] = status_filter.value
            
            agents = await self.db.agent.find_many(
                where=where_clause,
                skip=skip,
                take=size,
                order={"updatedAt": "desc"}
            )
            
            total = await self.db.agent.count(where=where_clause)
            
            return agents, total
            
        except Exception as e:
            logger.error("Failed to search agents", error=str(e), query=query)
            raise
    
    async def can_delete_agent(self, agent_id: str) -> Tuple[bool, Optional[str]]:
        """Check if agent can be deleted"""
        try:
            # Check for active workflows
            active_workflows = await self.db.workflow.count(
                where={
                    "agentId": agent_id,
                    "status": {"in": ["RUNNING", "PENDING"]}
                }
            )
            
            if active_workflows > 0:
                return False, f"Agent has {active_workflows} active workflow(s)"
            
            # Check for active conversations
            active_conversations = await self.db.conversationsession.count(
                where={
                    "agentId": agent_id,
                    "status": "ACTIVE"
                }
            )
            
            if active_conversations > 0:
                return False, f"Agent has {active_conversations} active conversation(s)"
            
            return True, None
            
        except Exception as e:
            logger.error("Failed to check if agent can be deleted", error=str(e), agent_id=agent_id)
            # If we can't check, allow deletion but log the error
            return True, None