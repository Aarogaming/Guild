"""
Guild Agent Coordinator - Multi-agent coordination and cooperation system
"""

import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from datetime import datetime, timezone, timedelta
import json

from .communication_hub import CommunicationChannel, MessagePriority
from .schema import (
    AgentStatus,
    AgentCapability,
    AgentRole,
    TaskPriority,
    normalize_agent_capability,
    normalize_agent_role,
    normalize_task_priority,
)


@dataclass
class Agent:
    """Enhanced agent representation with full coordination tracking"""

    id: str
    name: str
    status: AgentStatus
    capabilities: List[AgentCapability]
    current_tasks: Set[str] = field(default_factory=set)
    max_concurrent_tasks: int = 3
    last_heartbeat: Optional[str] = None
    last_activity: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    role: AgentRole = AgentRole.GENERAL
    domain_affinity: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "current_tasks": list(self.current_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "last_heartbeat": self.last_heartbeat,
            "last_activity": self.last_activity,
            "performance_metrics": self.performance_metrics,
            "metadata": self.metadata,
            "role": self.role.value,
            "domain_affinity": self.domain_affinity,
            "created_at": self.created_at,
        }


@dataclass
class CooperationRequest:
    """Request for agent cooperation"""

    id: str
    requesting_agent: str
    target_agent: Optional[str]  # None for broadcast
    request_type: str
    payload: Dict[str, Any]
    priority: MessagePriority
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    expires_at: Optional[str] = None
    responses: List[Dict[str, Any]] = field(default_factory=list)


class AgentCoordinator:
    """
    Multi-agent coordination and cooperation system.

    Features:
    - Agent registration and lifecycle management
    - Capability-based task routing
    - Load balancing and workload distribution
    - Agent health monitoring and heartbeat
    - Inter-agent communication and cooperation
    - Performance tracking and optimization
    - Fault tolerance and failover
    """

    def __init__(self, config, guild_core):
        self.config = config
        self.guild_core = guild_core
        self._running = False

        # Agent registry and indexing
        self._agents: Dict[str, Agent] = {}
        self._capability_index: Dict[AgentCapability, Set[str]] = {
            cap: set() for cap in AgentCapability
        }
        self._status_index: Dict[AgentStatus, Set[str]] = {
            status: set() for status in AgentStatus
        }

        # Cooperation system
        self._cooperation_requests: Dict[str, CooperationRequest] = {}
        self._cooperation_handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

        # Monitoring
        self._heartbeat_timeout = timedelta(minutes=5)
        self._monitoring_task: Optional[asyncio.Task] = None

        logger.info("Agent Coordinator initialized")

    async def start(self) -> None:
        """Start the agent coordinator"""
        if self._running:
            return

        self._running = True

        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        # Subscribe to communication events
        self.guild_core.communication_hub.subscribe(
            CommunicationChannel.AGENT_COORDINATION, self._handle_coordination_event
        )

        # Register built-in cooperation handlers
        self._register_cooperation_handlers()

        logger.info("Agent Coordinator started")

    async def stop(self) -> None:
        """Stop the agent coordinator"""
        if not self._running:
            return

        self._running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Agent Coordinator stopped")

    def _register_cooperation_handlers(self) -> None:
        """Register built-in cooperation request handlers"""
        self._cooperation_handlers.update(
            {
                "peer_review": self._handle_peer_review_request,
                "knowledge_share": self._handle_knowledge_share_request,
                "task_handoff": self._handle_task_handoff_request,
                "capability_query": self._handle_capability_query_request,
                "load_balance": self._handle_load_balance_request,
            }
        )

    async def register_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        max_concurrent_tasks: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
        role: Optional[str] = None,
        domain_affinity: Optional[List[str]] = None,
    ) -> bool:
        """Register a new agent"""
        try:
            # Convert string capabilities to enum
            agent_capabilities: List[AgentCapability] = []
            if capabilities:
                for cap_str in capabilities:
                    normalized = normalize_agent_capability(cap_str)
                    if normalized:
                        agent_capabilities.append(normalized)
                    else:
                        logger.warning(f"Unknown capability: {cap_str}")

            resolved_role = normalize_agent_role(role or (metadata or {}).get("role"))
            if resolved_role == AgentRole.GENERAL and name:
                inferred_role = self._infer_role_from_name(name)
                if inferred_role:
                    resolved_role = inferred_role
            resolved_domains = (
                domain_affinity
                if domain_affinity is not None
                else (metadata or {}).get("domain_affinity", [])
            )
            if resolved_domains:
                resolved_domains = [
                    str(d).strip().lower() for d in resolved_domains if d
                ]

            agent = Agent(
                id=agent_id,
                name=name or agent_id,
                status=AgentStatus.IDLE,
                capabilities=agent_capabilities,
                max_concurrent_tasks=max_concurrent_tasks,
                last_heartbeat=datetime.now(timezone.utc).isoformat(),
                metadata=metadata or {},
                role=resolved_role,
                domain_affinity=list(resolved_domains) if resolved_domains else [],
            )

            # Add to registry
            self._agents[agent_id] = agent

            # Update indexes
            for capability in agent_capabilities:
                self._capability_index[capability].add(agent_id)
            self._status_index[AgentStatus.IDLE].add(agent_id)

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "agent.registered",
                {
                    "agent_id": agent_id,
                    "name": agent.name,
                    "capabilities": capabilities or [],
                },
                CommunicationChannel.AGENT_COORDINATION,
                MessagePriority.NORMAL,
            )

            logger.info(
                f"Agent {agent_id} registered with capabilities: {capabilities or []}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        try:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]

            # Remove from indexes
            for capability in agent.capabilities:
                self._capability_index[capability].discard(agent_id)
            self._status_index[agent.status].discard(agent_id)

            # Remove from registry
            del self._agents[agent_id]

            # Emit event
            await self.guild_core.communication_hub.emit_event(
                "agent.unregistered",
                {"agent_id": agent_id},
                CommunicationChannel.AGENT_COORDINATION,
                MessagePriority.NORMAL,
            )

            logger.info(f"Agent {agent_id} unregistered")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def update_agent_status(
        self, agent_id: Optional[str] = None, status: Optional[AgentStatus] = None
    ) -> None:
        """Update agent status (or all agents if no specific agent)"""
        try:
            if agent_id:
                # Update specific agent
                if agent_id in self._agents and status:
                    agent = self._agents[agent_id]
                    old_status = agent.status

                    # Update status
                    agent.status = status
                    agent.last_activity = datetime.now(timezone.utc).isoformat()

                    # Update indexes
                    self._status_index[old_status].discard(agent_id)
                    self._status_index[status].add(agent_id)

                    # Emit event
                    await self.guild_core.communication_hub.emit_event(
                        "agent.status_changed",
                        {
                            "agent_id": agent_id,
                            "old_status": old_status.value,
                            "new_status": status.value,
                        },
                        CommunicationChannel.AGENT_COORDINATION,
                        MessagePriority.LOW,
                    )
            else:
                # Update all agents (periodic health check)
                for agent_id, agent in self._agents.items():
                    await self._update_agent_health(agent_id, agent)

        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")

    async def _update_agent_health(self, agent_id: str, agent: Agent) -> None:
        """Update individual agent health based on heartbeat and activity"""
        try:
            now = datetime.now(timezone.utc)

            # Check heartbeat timeout
            if agent.last_heartbeat:
                last_heartbeat = datetime.fromisoformat(
                    agent.last_heartbeat.replace("Z", "+00:00")
                )
                if now - last_heartbeat > self._heartbeat_timeout:
                    if agent.status != AgentStatus.OFFLINE:
                        await self._set_agent_status(agent_id, AgentStatus.OFFLINE)
                        logger.warning(
                            f"Agent {agent_id} marked offline due to heartbeat timeout"
                        )
                    return

            # Update status based on workload
            current_load = len(agent.current_tasks)

            if current_load == 0:
                target_status = AgentStatus.IDLE
            elif current_load >= agent.max_concurrent_tasks:
                target_status = AgentStatus.OVERLOADED
            else:
                target_status = AgentStatus.BUSY

            if agent.status != target_status and agent.status != AgentStatus.OFFLINE:
                await self._set_agent_status(agent_id, target_status)

        except Exception as e:
            logger.error(f"Failed to update health for agent {agent_id}: {e}")

    async def _set_agent_status(self, agent_id: str, status: AgentStatus) -> None:
        """Set agent status and update indexes"""
        if agent_id not in self._agents:
            return

        agent = self._agents[agent_id]
        old_status = agent.status

        # Update status
        agent.status = status
        agent.last_activity = datetime.now(timezone.utc).isoformat()

        # Update indexes
        self._status_index[old_status].discard(agent_id)
        self._status_index[status].add(agent_id)

    async def heartbeat(
        self, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record agent heartbeat"""
        try:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]
            agent.last_heartbeat = datetime.now(timezone.utc).isoformat()

            if metadata:
                agent.metadata.update(metadata)

            # If agent was offline, bring it back online
            if agent.status == AgentStatus.OFFLINE:
                await self._set_agent_status(agent_id, AgentStatus.IDLE)
                logger.info(f"Agent {agent_id} back online")

            return True

        except Exception as e:
            logger.error(f"Failed to record heartbeat for agent {agent_id}: {e}")
            return False

    async def assign_task(self, agent_id: str, task_id: str) -> bool:
        """Assign a task to an agent"""
        try:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]
            agent.current_tasks.add(task_id)

            # Update status based on new load
            await self._update_agent_health(agent_id, agent)

            return True

        except Exception as e:
            logger.error(f"Failed to assign task {task_id} to agent {agent_id}: {e}")
            return False

    async def unassign_task(self, agent_id: str, task_id: str) -> bool:
        """Unassign a task from an agent"""
        try:
            if agent_id not in self._agents:
                return False

            agent = self._agents[agent_id]
            agent.current_tasks.discard(task_id)

            # Update status based on new load
            await self._update_agent_health(agent_id, agent)

            return True

        except Exception as e:
            logger.error(
                f"Failed to unassign task {task_id} from agent {agent_id}: {e}"
            )
            return False

    async def find_capable_agents(
        self, required_capabilities: List[str], exclude_overloaded: bool = True
    ) -> List[str]:
        """Find agents with required capabilities"""
        try:
            # Convert string capabilities to enum
            required_caps = []
            for cap_str in required_capabilities:
                normalized = normalize_agent_capability(cap_str)
                if normalized:
                    required_caps.append(normalized)
                else:
                    logger.warning(f"Unknown capability: {cap_str}")
                    continue

            # Find agents with all required capabilities
            capable_agents = set()
            for i, capability in enumerate(required_caps):
                agents_with_cap = self._capability_index[capability]
                if i == 0:
                    capable_agents = agents_with_cap.copy()
                else:
                    capable_agents &= agents_with_cap

            # Filter by status if requested
            if exclude_overloaded:
                available_agents = (
                    self._status_index[AgentStatus.IDLE]
                    | self._status_index[AgentStatus.BUSY]
                )
                capable_agents &= available_agents

            return list(capable_agents)

        except Exception as e:
            logger.error(f"Failed to find capable agents: {e}")
            return []

    async def get_best_agent_for_task(
        self,
        required_capabilities: List[str],
        task_priority: str = "medium",
        task_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Get the best agent for a specific task based on capabilities and load"""
        try:
            capable_agents = await self.find_capable_agents(required_capabilities)

            if not capable_agents:
                return None

            normalized_priority = normalize_task_priority(task_priority)
            preferred_roles = self._infer_preferred_roles(
                required_capabilities, task_metadata or {}
            )
            preferred_domains = self._infer_preferred_domains(
                required_capabilities, task_metadata or {}
            )

            # Score agents based on availability and performance
            agent_scores = []

            for agent_id in capable_agents:
                agent = self._agents[agent_id]

                # Base score from availability
                if agent.status == AgentStatus.IDLE:
                    availability_score = 100
                elif agent.status == AgentStatus.BUSY:
                    load_ratio = len(agent.current_tasks) / agent.max_concurrent_tasks
                    availability_score = 100 * (1 - load_ratio)
                else:
                    availability_score = 0

                # Performance score (if available)
                performance_score = (
                    agent.performance_metrics.get("success_rate", 0.8) * 100
                )

                # Priority bonus for urgent tasks
                priority_bonus = (
                    20
                    if normalized_priority == TaskPriority.URGENT
                    and agent.status == AgentStatus.IDLE
                    else 0
                )

                # Role and domain affinity
                role_bonus = 15 if agent.role in preferred_roles else 0
                domain_bonus = 0
                if preferred_domains and agent.domain_affinity:
                    overlap = set(preferred_domains) & set(agent.domain_affinity)
                    domain_bonus = min(10, len(overlap) * 3)

                total_score = (
                    availability_score * 0.6
                    + performance_score * 0.3
                    + priority_bonus * 0.1
                    + role_bonus
                    + domain_bonus
                )
                agent_scores.append((agent_id, total_score))

            # Return agent with highest score
            agent_scores.sort(key=lambda x: x[1], reverse=True)
            return agent_scores[0][0] if agent_scores else None

        except Exception as e:
            logger.error(f"Failed to get best agent for task: {e}")
            return None

    async def request_cooperation(
        self,
        requesting_agent: str,
        request_type: str,
        payload: Dict[str, Any],
        target_agent: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout_minutes: int = 30,
    ) -> str:
        """Request cooperation from other agents"""
        try:
            import uuid

            request_id = str(uuid.uuid4())
            expires_at = None

            if timeout_minutes:
                expires_at = (
                    datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
                ).isoformat()

            cooperation_request = CooperationRequest(
                id=request_id,
                requesting_agent=requesting_agent,
                target_agent=target_agent,
                request_type=request_type,
                payload=payload,
                priority=priority,
                expires_at=expires_at,
            )

            self._cooperation_requests[request_id] = cooperation_request

            # Broadcast or send to specific agent
            await self.guild_core.communication_hub.emit_event(
                "cooperation.request",
                {
                    "request_id": request_id,
                    "requesting_agent": requesting_agent,
                    "target_agent": target_agent,
                    "request_type": request_type,
                    "payload": payload,
                },
                CommunicationChannel.AGENT_COORDINATION,
                priority,
            )

            logger.info(
                f"Cooperation request {request_id} created by {requesting_agent}"
            )
            return request_id

        except Exception as e:
            logger.error(f"Failed to create cooperation request: {e}")
            return ""

    async def respond_to_cooperation(
        self, request_id: str, responding_agent: str, response: Dict[str, Any]
    ) -> bool:
        """Respond to a cooperation request"""
        try:
            if request_id not in self._cooperation_requests:
                return False

            cooperation_request = self._cooperation_requests[request_id]

            # Check if request has expired
            if cooperation_request.expires_at:
                expires_at = datetime.fromisoformat(
                    cooperation_request.expires_at.replace("Z", "+00:00")
                )
                if datetime.now(timezone.utc) > expires_at:
                    logger.warning(f"Cooperation request {request_id} has expired")
                    return False

            # Add response
            cooperation_request.responses.append(
                {
                    "agent_id": responding_agent,
                    "response": response,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Notify requesting agent
            await self.guild_core.communication_hub.emit_event(
                "cooperation.response",
                {
                    "request_id": request_id,
                    "responding_agent": responding_agent,
                    "response": response,
                },
                CommunicationChannel.AGENT_COORDINATION,
                MessagePriority.NORMAL,
            )

            logger.info(
                f"Cooperation response from {responding_agent} for request {request_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to respond to cooperation request: {e}")
            return False

    async def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get capabilities for an agent"""
        if agent_id not in self._agents:
            return []

        agent = self._agents[agent_id]
        return [cap.value for cap in agent.capabilities]

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Agent]:
        """List all agents"""
        return list(self._agents.values())

    async def get_active_count(self) -> int:
        """Get count of active agents"""
        return len(self._status_index[AgentStatus.IDLE]) + len(
            self._status_index[AgentStatus.BUSY]
        )

    async def get_health(self) -> Dict[str, Any]:
        """Get health status of agent coordinator"""
        return {
            "status": "healthy" if self._running else "stopped",
            "total_agents": len(self._agents),
            "by_status": {
                status.value: len(agent_ids)
                for status, agent_ids in self._status_index.items()
            },
            "active_cooperation_requests": len(self._cooperation_requests),
            "capability_coverage": {
                cap.value: len(agent_ids)
                for cap, agent_ids in self._capability_index.items()
                if agent_ids
            },
        }

    async def _handle_coordination_event(self, message) -> None:
        """Handle agent coordination events"""
        try:
            event_type = message.event_type
            data = message.payload

            if event_type == "cooperation.request":
                await self._process_cooperation_request(data)
            elif event_type == "agent.heartbeat":
                await self.heartbeat(data.get("agent_id"), data.get("metadata"))
            # Add more event handlers as needed

        except Exception as e:
            logger.error(f"Failed to handle coordination event: {e}")

    async def _process_cooperation_request(self, data: Dict[str, Any]) -> None:
        """Process incoming cooperation request"""
        try:
            request_type = data.get("request_type")

            if request_type in self._cooperation_handlers:
                handler = self._cooperation_handlers[request_type]
                await handler(data)
            else:
                logger.warning(
                    f"No handler for cooperation request type: {request_type}"
                )

        except Exception as e:
            logger.error(f"Failed to process cooperation request: {e}")

    def _infer_preferred_roles(
        self, required_capabilities: List[str], metadata: Dict[str, Any]
    ) -> List[AgentRole]:
        preferred = []
        preferred_role = metadata.get("preferred_role")
        if preferred_role:
            preferred.append(normalize_agent_role(preferred_role))

        caps = {cap.lower() for cap in required_capabilities}
        if {"research", "analysis", "planning"} & caps:
            preferred.append(AgentRole.MERLIN)
        if {"home_automation", "home"} & caps:
            preferred.append(AgentRole.FORTRESS)
        if {"mobile_extension", "mobile", "android"} & caps:
            preferred.append(AgentRole.ANDROID_APP)
        if {"user_engagement", "ui", "desktop"} & caps:
            preferred.append(AgentRole.DESKTOP)

        if not preferred:
            preferred.append(AgentRole.GENERAL)
        return preferred

    def _infer_preferred_domains(
        self, required_capabilities: List[str], metadata: Dict[str, Any]
    ) -> List[str]:
        domains = []
        domain = metadata.get("domain")
        if domain:
            if isinstance(domain, str):
                domains.extend([d.strip() for d in domain.split(",") if d.strip()])
            elif isinstance(domain, list):
                domains.extend([str(d) for d in domain if d])

        caps = {cap.lower() for cap in required_capabilities}
        if "home_automation" in caps:
            domains.append("home")
        if "game_automation" in caps:
            domains.append("game")
        if "system_administration" in caps:
            domains.append("sysadmin")
        return list(dict.fromkeys(domains))

    def _infer_role_from_name(self, name: str) -> Optional[AgentRole]:
        normalized = name.strip().lower()
        if "merlin" in normalized:
            return AgentRole.MERLIN
        if "fortress" in normalized or "home" in normalized:
            return AgentRole.FORTRESS
        if "android" in normalized or "mobile" in normalized:
            return AgentRole.ANDROID_APP
        if "desktop" in normalized or "ui" in normalized:
            return AgentRole.DESKTOP
        return None

    # Built-in cooperation handlers

    async def _handle_peer_review_request(self, data: Dict[str, Any]) -> None:
        """Handle peer review cooperation request"""
        # Implementation for peer review coordination
        pass

    async def _handle_knowledge_share_request(self, data: Dict[str, Any]) -> None:
        """Handle knowledge sharing cooperation request"""
        # Implementation for knowledge sharing
        pass

    async def _handle_task_handoff_request(self, data: Dict[str, Any]) -> None:
        """Handle task handoff cooperation request"""
        # Implementation for task handoff between agents
        pass

    async def _handle_capability_query_request(self, data: Dict[str, Any]) -> None:
        """Handle capability query cooperation request"""
        # Implementation for capability discovery
        pass

    async def _handle_load_balance_request(self, data: Dict[str, Any]) -> None:
        """Handle load balancing cooperation request"""
        # Implementation for load balancing between agents
        pass

    async def _monitoring_loop(self) -> None:
        """Periodic monitoring and cleanup"""
        while self._running:
            try:
                # Update all agent statuses
                await self.update_agent_status()

                # Clean up expired cooperation requests
                await self._cleanup_expired_requests()

                await asyncio.sleep(30)  # Monitor every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)

    async def _cleanup_expired_requests(self) -> None:
        """Clean up expired cooperation requests"""
        try:
            now = datetime.now(timezone.utc)
            expired_requests = []

            for request_id, request in self._cooperation_requests.items():
                if request.expires_at:
                    expires_at = datetime.fromisoformat(
                        request.expires_at.replace("Z", "+00:00")
                    )
                    if now > expires_at:
                        expired_requests.append(request_id)

            for request_id in expired_requests:
                del self._cooperation_requests[request_id]
                logger.debug(f"Cleaned up expired cooperation request: {request_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup expired requests: {e}")
