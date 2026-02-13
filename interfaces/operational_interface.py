"""
Operational Interface for Guild System

This provides a clean, efficient interface for the hub, developers, and AI agents
to interact with the Guild system without getting lost in mystical complexity.

The interface abstracts away the fantasy elements while preserving the enhanced
functionality and engagement features.
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from datetime import datetime, timezone

# Import core systems
from ..core import GuildCore
from ..advanced.resource_aware_model_manager import ResourceAwareModelManager
from ..schema import (
    TaskPriority,
    TaskStatus,
    AgentCapability,
    AgentStatus,
    ExecutionMode,
    normalize_task_priority,
    normalize_task_status,
    normalize_agent_capability,
    normalize_execution_mode,
)
from ..advanced.mystical_guild import (
    MysticalGuild,
    MagicalElement,
    SpellType,
    MagicalRank,
)


@dataclass
class SimpleTask:
    """Simplified task representation"""

    id: str
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED
    created_at: str = ""
    completed_at: Optional[str] = None
    estimated_duration: int = 60  # minutes
    required_capabilities: Optional[List[AgentCapability]] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.required_capabilities is None:
            self.required_capabilities = []


@dataclass
class SimpleAgent:
    """Simplified agent representation"""

    id: str
    name: str
    capabilities: List[AgentCapability]
    current_load: float = 0.0  # 0.0 to 1.0
    performance_rating: float = 0.8  # 0.0 to 1.0
    specialization: Optional[str] = None
    available: bool = True
    mystical_id: Optional[str] = None


class GuildOperationalInterface:
    """
    Operational interface for efficient Guild system usage.

    This interface provides:
    - Simple task creation and management
    - Intelligent agent assignment
    - Resource-aware routing
    - Performance tracking
    - Clean API for hub/dev/AI integration

    The mystical elements run in the background to enhance engagement
    without complicating the operational workflow.
    """

    def __init__(self, enable_mystical_features: bool = True):
        # Core systems
        self.guild_core = GuildCore()
        self.resource_manager = self.guild_core.model_manager
        if not self.resource_manager:
            self.resource_manager = ResourceAwareModelManager(
                self.guild_core.config, self.guild_core
            )

        # Optional mystical enhancement
        self.mystical_guild = MysticalGuild() if enable_mystical_features else None
        self.mystical_enabled = enable_mystical_features

        # Performance tracking
        self.completion_stats: Dict[str, Any] = {
            "total_completed": 0,
            "average_completion_time": 0.0,
            "success_rate": 1.0,
            "agent_performance": {},
        }

        # Background processes
        self._running = False
        self.task_processor: Optional[asyncio.Task] = None

        logger.info("🎯 Guild Operational Interface initialized")

    async def start(self):
        """Start the operational interface"""
        if self._running:
            return

        self._running = True

        # Start core systems
        await self.guild_core.start()
        if (
            self.resource_manager
            and self.resource_manager is not self.guild_core.model_manager
        ):
            await self.resource_manager.start()

        # Start mystical enhancement if enabled
        if self.mystical_guild:
            await self.mystical_guild.start()
            logger.info("✨ Mystical enhancements active (background)")

        # Start task processing
        self.task_processor = asyncio.create_task(self._process_task_queue())

        logger.info("🚀 Guild Operational Interface started")

    async def stop(self):
        """Stop the operational interface"""
        if not self._running:
            return

        self._running = False

        # Stop task processing
        if self.task_processor:
            self.task_processor.cancel()
            try:
                await self.task_processor
            except asyncio.CancelledError:
                pass

        # Stop systems
        if self.mystical_guild:
            await self.mystical_guild.stop()

        if (
            self.resource_manager
            and self.resource_manager is not self.guild_core.model_manager
        ):
            await self.resource_manager.stop()
        await self.guild_core.stop()

        logger.info("✅ Guild Operational Interface stopped")

    # === TASK MANAGEMENT ===

    async def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        required_capabilities: Optional[List[AgentCapability]] = None,
        estimated_duration: int = 60,
        execution_mode: ExecutionMode | str = ExecutionMode.AUTOMATIC,
        execute_gate: bool = False,
    ) -> str:
        """Create a new task"""
        normalized_priority = normalize_task_priority(priority)
        capabilities = [cap.value for cap in (required_capabilities or [])]
        mode = normalize_execution_mode(execution_mode)

        task_id = await self.guild_core.task_director.create_task(
            title=title,
            description=description,
            priority=normalized_priority,
            capabilities_required=capabilities,
            metadata={
                "estimated_duration": estimated_duration,
                "execution_mode": mode.value,
                "execution_gate": execute_gate,
            },
        )

        # Mystical enhancement: Convert to quest if enabled
        if self.mystical_guild:
            await self._enhance_task_mystically(task_id, required_capabilities or [])

        logger.info(f"📝 Task created: {title} (ID: {task_id})")
        return task_id

    async def _enhance_task_mystically(
        self, task_id: str, required_capabilities: List[AgentCapability]
    ):
        """Enhance task with mystical elements (background)"""
        if not self.mystical_guild:
            return

        # Convert capabilities to magical elements
        capability_elements = {
            AgentCapability.CODE_GENERATION: MagicalElement.CODE,
            AgentCapability.OPTIMIZATION: MagicalElement.FIRE,
            AgentCapability.DEBUGGING: MagicalElement.WATER,
            AgentCapability.TESTING: MagicalElement.EARTH,
            AgentCapability.ANALYSIS: MagicalElement.AIR,
        }

        # Apply mystical enhancement based on task type
        if any(cap in required_capabilities for cap in [AgentCapability.OPTIMIZATION]):
            # Performance-critical task gets acceleration spell
            if self.mystical_guild.magical_agents:
                agent_id = list(self.mystical_guild.magical_agents.keys())[0]
                await self.mystical_guild.enchant_task(
                    task_id, SpellType.ACCELERATION, agent_id
                )

    def _to_simple_task(self, task) -> SimpleTask:
        caps = []
        for cap in task.capabilities_required:
            normalized = normalize_agent_capability(cap)
            if normalized:
                caps.append(normalized)
        return SimpleTask(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            assigned_agent=task.assignee,
            status=task.status,
            created_at=task.created_at,
            completed_at=task.completed_at,
            estimated_duration=task.metadata.get("estimated_duration", 60),
            required_capabilities=caps,
        )

    async def get_task(self, task_id: str) -> Optional[SimpleTask]:
        """Get task by ID"""
        task = await self.guild_core.task_director.get_task(task_id)
        if not task:
            return None
        return self._to_simple_task(task)

    async def update_task_status(
        self, task_id: str, status: str, completion_notes: str = ""
    ) -> bool:
        """Update task status"""
        resolved_status = normalize_task_status(status)
        metadata = {"completion_notes": completion_notes} if completion_notes else {}

        updated = await self.guild_core.task_director.set_task_status(
            task_id, resolved_status, metadata=metadata
        )
        if updated and resolved_status == TaskStatus.DONE:
            await self._record_task_completion(task_id)

        return updated

    async def _record_task_completion(self, task_id: str):
        """Record task completion for performance tracking"""
        task = await self.guild_core.task_director.get_task(task_id)
        if not task:
            return

        # Update completion stats
        self.completion_stats["total_completed"] += 1

        # Calculate completion time
        if task.completed_at and task.created_at:
            start_time = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(task.completed_at.replace("Z", "+00:00"))
            completion_time = (end_time - start_time).total_seconds() / 60.0  # minutes

            # Update average
            total = self.completion_stats["total_completed"]
            current_avg = self.completion_stats["average_completion_time"]
            self.completion_stats["average_completion_time"] = (
                current_avg * (total - 1) + completion_time
            ) / total

        # Update agent performance if assigned
        if task.assignee:
            agent_stats = self.completion_stats["agent_performance"].get(
                task.assignee, {"completed": 0, "avg_time": 0.0}
            )
            agent_stats["completed"] += 1
            self.completion_stats["agent_performance"][task.assignee] = agent_stats

    # === AGENT MANAGEMENT ===

    async def register_agent(
        self,
        name: str,
        capabilities: List[AgentCapability],
        specialization: Optional[str] = None,
        role: Optional[str] = None,
        domain_affinity: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        """Register a new agent"""
        import uuid

        agent_id = agent_id or f"agent_{uuid.uuid4().hex[:8]}"
        metadata = {"specialization": specialization} if specialization else {}

        await self.guild_core.agent_coordinator.register_agent(
            agent_id=agent_id,
            name=name,
            capabilities=[cap.value for cap in capabilities],
            metadata=metadata,
            role=role,
            domain_affinity=domain_affinity,
        )

        # Mystical enhancement: Create magical agent if enabled
        if self.mystical_guild:
            mystical_id = await self._create_mystical_agent(name, capabilities)
            if mystical_id:
                metadata["mystical_id"] = mystical_id

        logger.info(f"👤 Agent registered: {name} (ID: {agent_id})")
        return agent_id

    async def _create_mystical_agent(
        self, agent_name: str, capabilities: List[AgentCapability]
    ) -> Optional[str]:
        """Create corresponding mystical agent (background)"""
        if not self.mystical_guild:
            return None

        # Map capabilities to magical elements
        element_mapping = {
            AgentCapability.CODE_GENERATION: MagicalElement.CODE,
            AgentCapability.OPTIMIZATION: MagicalElement.FIRE,
            AgentCapability.DEBUGGING: MagicalElement.WATER,
            AgentCapability.TESTING: MagicalElement.EARTH,
            AgentCapability.ANALYSIS: MagicalElement.AIR,
        }

        # Choose primary element based on capabilities
        primary_element = MagicalElement.CODE  # default
        for capability in capabilities:
            if capability in element_mapping:
                primary_element = element_mapping[capability]
                break

        # Create mystical agent
        mystical_agent_id = await self.mystical_guild.create_magical_agent(
            agent_name, primary_element, MagicalRank.ADEPT
        )
        return mystical_agent_id

    async def get_available_agents(
        self, required_capabilities: Optional[List[AgentCapability]] = None
    ) -> List[SimpleAgent]:
        """Get available agents, optionally filtered by capabilities"""
        agents = await self.list_agents()
        if required_capabilities:
            agents = [
                agent
                for agent in agents
                if any(cap in agent.capabilities for cap in required_capabilities)
            ]
        agents.sort(key=lambda a: (a.current_load, -a.performance_rating))
        return agents

    async def list_agents(self, available_only: bool = False) -> List[SimpleAgent]:
        """List all agents in the system."""
        agents = self.guild_core.agent_coordinator.list_agents()
        simple_agents = []
        for agent in agents:
            caps = list(agent.capabilities)
            current_load = 0.0
            if agent.max_concurrent_tasks:
                current_load = len(agent.current_tasks) / agent.max_concurrent_tasks
            available = agent.status in {AgentStatus.IDLE, AgentStatus.BUSY}
            if available_only and not available:
                continue
            simple_agents.append(
                SimpleAgent(
                    id=agent.id,
                    name=agent.name,
                    capabilities=caps,
                    current_load=current_load,
                    performance_rating=agent.performance_metrics.get(
                        "success_rate", 0.8
                    ),
                    specialization=agent.metadata.get("specialization"),
                    available=available,
                    mystical_id=agent.metadata.get("mystical_id"),
                )
            )
        return simple_agents

    async def list_tasks(self, status: Optional[str] = None) -> List[SimpleTask]:
        """List tasks with optional status filter."""
        task_status = normalize_task_status(status) if status else None
        tasks = await self.guild_core.task_director.list_tasks(status=task_status)
        return [self._to_simple_task(task) for task in tasks]

    async def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to a specific agent"""
        task = await self.guild_core.task_director.get_task(task_id)
        if not task:
            return False

        claimed = await self.guild_core.task_director.claim_task(agent_id, task_id)
        if not claimed:
            return False

        await self.guild_core.agent_coordinator.assign_task(agent_id, task_id)
        logger.info(f"🎯 Task {task_id} assigned to {agent_id}")
        return True

    async def start_execution(self, task_id: str, agent_id: str) -> bool:
        """Start execution after execute gate approval."""
        return await self.guild_core.task_director.start_execution(task_id, agent_id)

    # === INTELLIGENT ROUTING ===

    async def auto_assign_task(self, task_id: str) -> bool:
        """Automatically assign task to best available agent"""
        task = await self.guild_core.task_director.get_task(task_id)
        if not task:
            return False

        mode = normalize_execution_mode(task.metadata.get("execution_mode"))
        if mode in {ExecutionMode.MANUAL, ExecutionMode.SEMI_AUTOMATIC}:
            logger.info(f"Skipping auto-assign for {task_id} (mode={mode.value})")
            return False
        if mode == ExecutionMode.AGENT_ASSISTED and not task.metadata.get(
            "preferred_role"
        ):
            task.metadata["preferred_role"] = "merlin"

        if not task.capabilities_required:
            logger.warning(f"Task {task_id} has no required capabilities")

        best_agent = await self.guild_core.agent_coordinator.get_best_agent_for_task(
            task.capabilities_required,
            task.priority.value,
            task.metadata,
        )
        if not best_agent:
            logger.warning(f"No available agents for task {task_id}")
            return False

        return await self.assign_task_to_agent(task_id, best_agent)

    # === TASK PROCESSING ===

    async def _process_task_queue(self):
        """Process the task queue continuously"""
        while self._running:
            try:
                queued_tasks = await self.guild_core.task_director.list_tasks(
                    status=TaskStatus.QUEUED
                )
                if queued_tasks:
                    priority_order = {
                        TaskPriority.CRITICAL: 0,
                        TaskPriority.URGENT: 1,
                        TaskPriority.HIGH: 2,
                        TaskPriority.MEDIUM: 3,
                        TaskPriority.LOW: 4,
                    }
                    queued_tasks.sort(key=lambda t: priority_order.get(t.priority, 3))
                    await self.auto_assign_task(queued_tasks[0].id)

                await asyncio.sleep(5)  # Check every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task processing error: {e}")
                await asyncio.sleep(10)

    # === STATUS AND MONITORING ===

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        tasks = await self.guild_core.task_director.list_tasks()
        by_status = {status: 0 for status in TaskStatus}
        for task in tasks:
            by_status[task.status] += 1

        total_tasks = len(tasks)
        pending_tasks = by_status[TaskStatus.QUEUED] + by_status[TaskStatus.BLOCKED]
        active_tasks = by_status[TaskStatus.IN_PROGRESS]
        completed_tasks = by_status[TaskStatus.DONE]

        agents = self.guild_core.agent_coordinator.list_agents()
        total_agents = len(agents)
        available_agents = len(
            [a for a in agents if a.status in {AgentStatus.IDLE, AgentStatus.BUSY}]
        )
        busy_agents = len([a for a in agents if a.status == AgentStatus.BUSY])

        resource_status = (
            self.resource_manager.get_resource_aware_status()
            if self.resource_manager
            else {}
        )
        if resource_status and "current_metrics" in resource_status:
            metrics = resource_status.get("current_metrics") or {}
            resource_status.setdefault("cpu_usage", metrics.get("cpu_percent", 0.0))
            resource_status.setdefault(
                "memory_usage", metrics.get("memory_percent", 0.0)
            )

        status = {
            "system_running": self._running,
            "mystical_features_enabled": self.mystical_enabled,
            # Task statistics
            "tasks": {
                "total": total_tasks,
                "pending": pending_tasks,
                "active": active_tasks,
                "completed": completed_tasks,
                "queue_length": by_status[TaskStatus.QUEUED],
            },
            # Agent statistics
            "agents": {
                "total": total_agents,
                "available": available_agents,
                "busy": busy_agents,
            },
            # Performance statistics
            "performance": self.completion_stats,
            # Resource status
            "resources": resource_status,
            # Mystical status (if enabled)
            "mystical_status": None,
        }

        # Add mystical status if enabled
        if self.mystical_guild:
            mystical_status = self.mystical_guild.get_mystical_status()
            status["mystical_status"] = {
                "magical_agents": mystical_status["magical_agents"],
                "guild_mana_pool": mystical_status["guild_mana_pool"],
                "active_spells": len(mystical_status.get("enchanted_tasks", {})),
                "digital_dragons": mystical_status["digital_dragons"],
            }

        return status

    async def get_task_recommendations(self, agent_id: str) -> List[str]:
        """Get task recommendations for a specific agent"""
        agent = self.guild_core.agent_coordinator.get_agent(agent_id)
        if not agent:
            return []

        queued_tasks = await self.guild_core.task_director.list_tasks(
            status=TaskStatus.QUEUED
        )

        suitable_tasks = []
        agent_caps = {cap.value for cap in agent.capabilities}
        for task in queued_tasks:
            if any(cap in agent_caps for cap in task.capabilities_required):
                suitable_tasks.append(task)

        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.URGENT: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4,
        }
        suitable_tasks.sort(
            key=lambda t: (
                priority_order.get(t.priority, 3),
                t.metadata.get("estimated_duration", 60),
            )
        )

        return [task.id for task in suitable_tasks[:5]]

    # === SIMPLE API METHODS FOR EXTERNAL INTEGRATION ===

    async def submit_work_request(
        self,
        title: str,
        description: str,
        priority: str = "normal",
        capabilities: Optional[List[str]] = None,
        estimated_minutes: int = 60,
        execution_mode: str | ExecutionMode = ExecutionMode.AUTOMATIC,
        execute_gate: bool = False,
    ) -> Dict[str, Any]:
        """Simple API for submitting work requests"""
        task_priority = normalize_task_priority(priority)

        # Convert string capabilities to enums
        capability_map = {
            "code": AgentCapability.CODE_GENERATION,
            "review": AgentCapability.CODE_REVIEW,
            "test": AgentCapability.TESTING,
            "debug": AgentCapability.DEBUGGING,
            "optimize": AgentCapability.OPTIMIZATION,
            "docs": AgentCapability.DOCUMENTATION,
            "analyze": AgentCapability.ANALYSIS,
            "research": AgentCapability.RESEARCH,
        }

        required_caps = []
        if capabilities:
            for cap in capabilities:
                if cap.lower() in capability_map:
                    required_caps.append(capability_map[cap.lower()])

        # Create task
        task_id = await self.create_task(
            title=title,
            description=description,
            priority=task_priority,
            required_capabilities=required_caps,
            estimated_duration=estimated_minutes,
            execution_mode=execution_mode,
            execute_gate=execute_gate,
        )

        queued_count = len(
            await self.guild_core.task_director.list_tasks(status=TaskStatus.QUEUED)
        )

        return {
            "task_id": task_id,
            "status": "created",
            "estimated_completion": f"{estimated_minutes} minutes",
            "queue_position": queued_count,
        }

    async def check_work_status(self, task_id: str) -> Dict[str, Any]:
        """Simple API for checking work status"""

        task = await self.get_task(task_id)
        if not task:
            return {"error": "Task not found"}

        result = {
            "task_id": task_id,
            "title": task.title,
            "status": task.status.value,
            "created_at": task.created_at,
            "assigned_agent": task.assigned_agent,
        }

        if task.completed_at:
            result["completed_at"] = task.completed_at

        if task.assigned_agent:
            agent = self.guild_core.agent_coordinator.get_agent(task.assigned_agent)
            if agent:
                result["agent_name"] = agent.name

        return result


# Convenience function for easy initialization
async def create_operational_guild(
    enable_mystical: bool = True,
) -> GuildOperationalInterface:
    """Create and start an operational guild interface"""

    guild = GuildOperationalInterface(enable_mystical_features=enable_mystical)
    await guild.start()

    # Register some default agents
    await guild.register_agent(
        "Code Generator AI",
        [AgentCapability.CODE_GENERATION, AgentCapability.DOCUMENTATION],
        "Python and JavaScript development",
        agent_id="codegen",
    )

    await guild.register_agent(
        "Merlin",
        [
            AgentCapability.PLANNING,
            AgentCapability.RESEARCH,
            AgentCapability.ANALYSIS,
            AgentCapability.DOCUMENTATION,
            AgentCapability.AI_ASSISTANCE,
        ],
        "Planning, research, and user assistance",
        role="merlin",
        agent_id="merlin",
    )

    await guild.register_agent(
        "Fortress",
        [AgentCapability.HOME_AUTOMATION, AgentCapability.SYSTEM_ADMINISTRATION],
        "Home-link sector",
        role="fortress",
        agent_id="fortress",
    )

    await guild.register_agent(
        "AndroidApp",
        [AgentCapability.MOBILE_EXTENSION, AgentCapability.USER_ENGAGEMENT],
        "Mobile extension",
        role="androidapp",
        agent_id="androidapp",
    )

    await guild.register_agent(
        "Desktop",
        [AgentCapability.USER_ENGAGEMENT, AgentCapability.DOCUMENTATION],
        "User engagement",
        role="desktop",
        agent_id="desktop",
    )

    await guild.register_agent(
        "Debug Specialist AI",
        [AgentCapability.DEBUGGING, AgentCapability.TESTING, AgentCapability.ANALYSIS],
        "Error detection and resolution",
        agent_id="debugger",
    )

    await guild.register_agent(
        "Performance Optimizer AI",
        [AgentCapability.OPTIMIZATION, AgentCapability.ANALYSIS],
        "Performance tuning and optimization",
        agent_id="optimizer",
    )

    logger.info("🎯 Operational Guild ready for use")
    return guild
