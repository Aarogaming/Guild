"""
AI Agent Interface for Guild System

This provides a clean, efficient interface for AI agents to interact with
the Guild system, register themselves, receive tasks, and report progress.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger
from datetime import datetime, timezone

from .operational_interface import (
    GuildOperationalInterface,
    TaskPriority,
    AgentCapability,
    SimpleTask,
    SimpleAgent,
)


class AgentStatus(Enum):
    """AI Agent status"""

    INITIALIZING = "initializing"
    AVAILABLE = "available"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class TaskProgress:
    """Task progress report"""

    task_id: str
    progress_percentage: float  # 0.0 to 100.0
    status_message: str
    estimated_completion: Optional[str] = None
    intermediate_results: Optional[Dict[str, Any]] = None
    issues_encountered: List[str] = None

    def __post_init__(self):
        if self.issues_encountered is None:
            self.issues_encountered = []


@dataclass
class AgentCapabilities:
    """Detailed agent capabilities"""

    primary_skills: List[AgentCapability]
    secondary_skills: List[AgentCapability]
    specializations: List[str]
    performance_metrics: Dict[str, float]
    resource_requirements: Dict[str, Any]
    supported_languages: List[str]
    max_concurrent_tasks: int = 1


class AIAgentInterface:
    """
    Interface for AI agents to interact with the Guild system.

    Provides:
    - Agent registration and capability declaration
    - Task reception and progress reporting
    - Resource management and load balancing
    - Performance tracking and optimization
    - Error handling and recovery
    """

    def __init__(self, agent_name: str, agent_id: str = None):
        self.agent_name = agent_name
        self.agent_id = agent_id or f"ai_agent_{agent_name.lower().replace(' ', '_')}"

        # Guild connection
        self.guild: GuildOperationalInterface = None
        self.registered = False

        # Agent state
        self.status = AgentStatus.INITIALIZING
        self.capabilities: AgentCapabilities = None
        self.current_tasks: Dict[str, SimpleTask] = {}
        self.task_history: List[Dict[str, Any]] = []

        # Performance tracking
        self.performance_stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_completion_time": 0.0,
            "success_rate": 1.0,
            "total_runtime": 0.0,
        }

        # Callbacks for task handling
        self.task_handlers: Dict[str, Callable] = {}
        self.progress_callback: Optional[Callable] = None

        # Background processes
        self._running = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.task_monitor_task: Optional[asyncio.Task] = None

        logger.info(f"🤖 AI Agent Interface initialized: {self.agent_name}")

    async def connect_to_guild(self, guild: GuildOperationalInterface):
        """Connect to the Guild system"""

        self.guild = guild
        logger.info(f"🔌 {self.agent_name} connected to Guild system")

    async def register_capabilities(self, capabilities: AgentCapabilities):
        """Register agent capabilities with the Guild"""

        if not self.guild:
            raise RuntimeError("Must connect to Guild before registering capabilities")

        self.capabilities = capabilities

        # Register with the Guild operational interface
        guild_agent_id = await self.guild.register_agent(
            name=self.agent_name,
            capabilities=capabilities.primary_skills + capabilities.secondary_skills,
            specialization=", ".join(capabilities.specializations),
        )

        # Update our agent record in the guild
        if guild_agent_id in self.guild.agents:
            guild_agent = self.guild.agents[guild_agent_id]
            guild_agent.performance_rating = capabilities.performance_metrics.get(
                "base_rating", 0.8
            )

        self.registered = True
        self.status = AgentStatus.AVAILABLE

        logger.info(f"✅ {self.agent_name} registered with Guild")
        logger.info(
            f"   Primary skills: {[skill.value for skill in capabilities.primary_skills]}"
        )
        logger.info(f"   Specializations: {capabilities.specializations}")

    async def start(self):
        """Start the AI agent interface"""

        if not self.registered:
            raise RuntimeError("Must register capabilities before starting")

        self._running = True

        # Start background processes
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.task_monitor_task = asyncio.create_task(self._task_monitor_loop())

        logger.info(f"🚀 {self.agent_name} started and ready for tasks")

    async def stop(self):
        """Stop the AI agent interface"""

        self._running = False
        self.status = AgentStatus.OFFLINE

        # Stop background processes
        for task in [self.heartbeat_task, self.task_monitor_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Complete any remaining tasks
        for task_id in list(self.current_tasks.keys()):
            await self.report_task_completion(
                task_id, success=False, result="Agent shutting down"
            )

        logger.info(f"✅ {self.agent_name} stopped")

    # === TASK HANDLING ===

    def register_task_handler(self, capability: AgentCapability, handler: Callable):
        """Register a handler function for a specific capability"""

        self.task_handlers[capability.value] = handler
        logger.info(f"📝 Registered handler for {capability.value}")

    async def request_task(
        self, preferred_capabilities: List[AgentCapability] = None
    ) -> Optional[SimpleTask]:
        """Request a task from the Guild"""

        if not self.guild or self.status != AgentStatus.AVAILABLE:
            return None

        # Check if we have capacity for more tasks
        if len(self.current_tasks) >= self.capabilities.max_concurrent_tasks:
            return None

        # Get task recommendations
        capability_strings = []
        if preferred_capabilities:
            capability_strings = [cap.value for cap in preferred_capabilities]
        elif self.capabilities:
            capability_strings = [cap.value for cap in self.capabilities.primary_skills]

        # Find suitable tasks in the queue
        for task_id in self.guild.task_queue[
            :
        ]:  # Copy to avoid modification during iteration
            task = self.guild.tasks.get(task_id)
            if not task or task.status != "pending":
                continue

            # Check if we can handle this task
            task_caps = [cap.value for cap in task.required_capabilities]
            if not task_caps or any(cap in capability_strings for cap in task_caps):
                # Try to assign the task to ourselves
                success = await self.guild.assign_task_to_agent(task_id, self.agent_id)
                if success:
                    self.current_tasks[task_id] = task
                    self.status = (
                        AgentStatus.BUSY
                        if len(self.current_tasks)
                        >= self.capabilities.max_concurrent_tasks
                        else AgentStatus.AVAILABLE
                    )

                    logger.info(f"📋 {self.agent_name} received task: {task.title}")
                    return task

        return None

    async def accept_task_assignment(self, task: SimpleTask) -> bool:
        """Accept a task assignment from the Guild"""

        if len(self.current_tasks) >= self.capabilities.max_concurrent_tasks:
            logger.warning(
                f"❌ {self.agent_name} at capacity, cannot accept task {task.id}"
            )
            return False

        # Check if we have a handler for this task
        task_caps = [cap.value for cap in task.required_capabilities]
        our_caps = [
            cap.value
            for cap in (
                self.capabilities.primary_skills + self.capabilities.secondary_skills
            )
        ]

        if not any(cap in our_caps for cap in task_caps):
            logger.warning(
                f"❌ {self.agent_name} cannot handle task capabilities: {task_caps}"
            )
            return False

        # Accept the task
        self.current_tasks[task.id] = task
        self.status = (
            AgentStatus.BUSY
            if len(self.current_tasks) >= self.capabilities.max_concurrent_tasks
            else AgentStatus.AVAILABLE
        )

        # Start processing the task
        asyncio.create_task(self._process_task(task))

        logger.info(f"✅ {self.agent_name} accepted task: {task.title}")
        return True

    async def _process_task(self, task: SimpleTask):
        """Process a task using registered handlers"""

        try:
            # Update task status
            await self.guild.update_task_status(task.id, "in_progress")

            # Find appropriate handler
            handler = None
            for cap in task.required_capabilities:
                if cap.value in self.task_handlers:
                    handler = self.task_handlers[cap.value]
                    break

            if not handler:
                # Use default handler if available
                handler = self.task_handlers.get("default")

            if handler:
                # Execute the handler
                result = await handler(task)

                # Report completion
                await self.report_task_completion(task.id, success=True, result=result)
            else:
                # No handler available
                await self.report_task_completion(
                    task.id,
                    success=False,
                    result="No handler available for task capabilities",
                )

        except Exception as e:
            logger.error(f"❌ Error processing task {task.id}: {e}")
            await self.report_task_completion(task.id, success=False, result=str(e))

    async def report_task_progress(self, task_id: str, progress: TaskProgress):
        """Report progress on a task"""

        if task_id not in self.current_tasks:
            logger.warning(f"❌ Cannot report progress for unknown task: {task_id}")
            return

        # Update task status if needed
        if progress.progress_percentage >= 100.0:
            await self.guild.update_task_status(task_id, "completed")

        # Call progress callback if registered
        if self.progress_callback:
            await self.progress_callback(task_id, progress)

        logger.info(
            f"📊 {self.agent_name} progress on {task_id}: {progress.progress_percentage:.1f}%"
        )

    async def report_task_completion(
        self, task_id: str, success: bool, result: Any = None
    ):
        """Report task completion"""

        if task_id not in self.current_tasks:
            logger.warning(f"❌ Cannot complete unknown task: {task_id}")
            return

        task = self.current_tasks[task_id]

        # Update task status
        final_status = "completed" if success else "failed"
        await self.guild.update_task_status(task_id, final_status)

        # Update performance stats
        self.performance_stats["tasks_completed" if success else "tasks_failed"] += 1

        # Calculate completion time
        start_time = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
        completion_time = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() / 60.0

        # Update average completion time
        total_completed = self.performance_stats["tasks_completed"]
        if total_completed > 0:
            current_avg = self.performance_stats["average_completion_time"]
            self.performance_stats["average_completion_time"] = (
                current_avg * (total_completed - 1) + completion_time
            ) / total_completed

        # Update success rate
        total_tasks = (
            self.performance_stats["tasks_completed"]
            + self.performance_stats["tasks_failed"]
        )
        self.performance_stats["success_rate"] = (
            self.performance_stats["tasks_completed"] / total_tasks
        )

        # Store in history
        self.task_history.append(
            {
                "task_id": task_id,
                "title": task.title,
                "success": success,
                "completion_time": completion_time,
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Remove from current tasks
        del self.current_tasks[task_id]

        # Update status
        self.status = (
            AgentStatus.AVAILABLE if len(self.current_tasks) == 0 else AgentStatus.BUSY
        )

        status_icon = "✅" if success else "❌"
        logger.info(f"{status_icon} {self.agent_name} completed task: {task.title}")

        if result:
            logger.info(f"   Result: {str(result)[:100]}...")

    # === BACKGROUND PROCESSES ===

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to Guild"""

        while self._running:
            try:
                # Update our agent status in the guild
                if self.guild and self.agent_id in self.guild.agents:
                    guild_agent = self.guild.agents[self.agent_id]
                    guild_agent.available = self.status == AgentStatus.AVAILABLE
                    guild_agent.current_load = (
                        len(self.current_tasks) / self.capabilities.max_concurrent_tasks
                    )
                    guild_agent.performance_rating = self.performance_stats[
                        "success_rate"
                    ]

                await asyncio.sleep(30)  # Heartbeat every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error for {self.agent_name}: {e}")
                await asyncio.sleep(10)

    async def _task_monitor_loop(self):
        """Monitor for new task assignments"""

        while self._running:
            try:
                # Check for new tasks if we have capacity
                if (
                    self.status == AgentStatus.AVAILABLE
                    and len(self.current_tasks) < self.capabilities.max_concurrent_tasks
                ):

                    task = await self.request_task()
                    if task:
                        # Task was assigned and is being processed
                        pass

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task monitor error for {self.agent_name}: {e}")
                await asyncio.sleep(30)

    # === STATUS AND MONITORING ===

    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "registered": self.registered,
            "current_tasks": len(self.current_tasks),
            "max_concurrent_tasks": (
                self.capabilities.max_concurrent_tasks if self.capabilities else 1
            ),
            "performance_stats": self.performance_stats,
            "capabilities": {
                "primary_skills": (
                    [skill.value for skill in self.capabilities.primary_skills]
                    if self.capabilities
                    else []
                ),
                "secondary_skills": (
                    [skill.value for skill in self.capabilities.secondary_skills]
                    if self.capabilities
                    else []
                ),
                "specializations": (
                    self.capabilities.specializations if self.capabilities else []
                ),
            },
            "task_history_count": len(self.task_history),
            "uptime": self.performance_stats["total_runtime"],
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""

        return {
            "tasks_completed": self.performance_stats["tasks_completed"],
            "tasks_failed": self.performance_stats["tasks_failed"],
            "success_rate": self.performance_stats["success_rate"],
            "average_completion_time": self.performance_stats[
                "average_completion_time"
            ],
            "current_load": len(self.current_tasks)
            / (self.capabilities.max_concurrent_tasks if self.capabilities else 1),
            "recent_tasks": self.task_history[-10:] if self.task_history else [],
        }

    # === UTILITY METHODS ===

    async def set_maintenance_mode(self, enabled: bool, reason: str = ""):
        """Set maintenance mode"""

        if enabled:
            self.status = AgentStatus.MAINTENANCE
            logger.info(f"🔧 {self.agent_name} entering maintenance mode: {reason}")
        else:
            self.status = AgentStatus.AVAILABLE
            logger.info(f"✅ {self.agent_name} exiting maintenance mode")

    async def update_capabilities(self, new_capabilities: AgentCapabilities):
        """Update agent capabilities"""

        self.capabilities = new_capabilities

        # Update in guild if registered
        if self.guild and self.agent_id in self.guild.agents:
            guild_agent = self.guild.agents[self.agent_id]
            guild_agent.capabilities = (
                new_capabilities.primary_skills + new_capabilities.secondary_skills
            )
            guild_agent.specialization = ", ".join(new_capabilities.specializations)

        logger.info(f"🔄 {self.agent_name} capabilities updated")

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress reporting"""
        self.progress_callback = callback


# === CONVENIENCE FUNCTIONS ===


async def create_ai_agent(
    agent_name: str,
    primary_skills: List[AgentCapability],
    specializations: List[str] = None,
    guild: GuildOperationalInterface = None,
) -> AIAgentInterface:
    """Create and register an AI agent"""

    agent = AIAgentInterface(agent_name)

    if guild:
        await agent.connect_to_guild(guild)

    capabilities = AgentCapabilities(
        primary_skills=primary_skills,
        secondary_skills=[],
        specializations=specializations or [],
        performance_metrics={"base_rating": 0.8},
        resource_requirements={},
        supported_languages=["python", "javascript", "typescript"],
        max_concurrent_tasks=2,
    )

    await agent.register_capabilities(capabilities)

    return agent


# === EXAMPLE AGENT IMPLEMENTATIONS ===


class CodeGenerationAgent(AIAgentInterface):
    """Example specialized code generation agent"""

    def __init__(self):
        super().__init__("Code Generation Specialist")

    async def initialize(self, guild: GuildOperationalInterface):
        """Initialize the code generation agent"""

        await self.connect_to_guild(guild)

        capabilities = AgentCapabilities(
            primary_skills=[AgentCapability.CODE_GENERATION],
            secondary_skills=[AgentCapability.DOCUMENTATION],
            specializations=["Python", "JavaScript", "API Development"],
            performance_metrics={"base_rating": 0.9},
            resource_requirements={"min_memory_gb": 4},
            supported_languages=["python", "javascript", "typescript", "go"],
            max_concurrent_tasks=3,
        )

        await self.register_capabilities(capabilities)

        # Register task handler
        self.register_task_handler(
            AgentCapability.CODE_GENERATION, self._handle_code_generation
        )

        await self.start()

    async def _handle_code_generation(self, task: SimpleTask) -> str:
        """Handle code generation tasks"""

        logger.info(f"🔨 Generating code for: {task.title}")

        # Report progress
        await self.report_task_progress(
            task.id,
            TaskProgress(
                task_id=task.id,
                progress_percentage=25.0,
                status_message="Analyzing requirements",
            ),
        )

        # Simulate code generation work
        await asyncio.sleep(2)

        await self.report_task_progress(
            task.id,
            TaskProgress(
                task_id=task.id,
                progress_percentage=75.0,
                status_message="Generating code",
            ),
        )

        await asyncio.sleep(3)

        # Return generated code (simulated)
        generated_code = f"""
# Generated code for: {task.title}
# Description: {task.description}

def generated_function():
    '''
    Auto-generated function based on task requirements.
    '''
    # Implementation would go here
    return "Task completed successfully"

if __name__ == "__main__":
    result = generated_function()
    print(result)
"""

        return generated_code


class DebuggingAgent(AIAgentInterface):
    """Example specialized debugging agent"""

    def __init__(self):
        super().__init__("Debug Specialist")

    async def initialize(self, guild: GuildOperationalInterface):
        """Initialize the debugging agent"""

        await self.connect_to_guild(guild)

        capabilities = AgentCapabilities(
            primary_skills=[AgentCapability.DEBUGGING],
            secondary_skills=[AgentCapability.TESTING, AgentCapability.ANALYSIS],
            specializations=["Error Analysis", "Performance Debugging", "Memory Leaks"],
            performance_metrics={"base_rating": 0.85},
            resource_requirements={"min_memory_gb": 8},
            supported_languages=["python", "javascript", "java", "c++"],
            max_concurrent_tasks=2,
        )

        await self.register_capabilities(capabilities)

        # Register task handler
        self.register_task_handler(AgentCapability.DEBUGGING, self._handle_debugging)

        await self.start()

    async def _handle_debugging(self, task: SimpleTask) -> str:
        """Handle debugging tasks"""

        logger.info(f"🐛 Debugging: {task.title}")

        # Simulate debugging process
        debug_steps = [
            (20, "Analyzing error logs"),
            (40, "Identifying root cause"),
            (60, "Developing fix strategy"),
            (80, "Implementing solution"),
            (100, "Verifying fix"),
        ]

        for progress, message in debug_steps:
            await self.report_task_progress(
                task.id,
                TaskProgress(
                    task_id=task.id,
                    progress_percentage=progress,
                    status_message=message,
                ),
            )
            await asyncio.sleep(1)

        return f"Debug analysis complete for: {task.title}. Root cause identified and fix implemented."


if __name__ == "__main__":

    async def demo_ai_agent():
        """Demonstrate AI agent interface"""

        from .operational_interface import create_operational_guild

        # Create guild
        guild = await create_operational_guild(enable_mystical=False)

        # Create specialized agents
        code_agent = CodeGenerationAgent()
        debug_agent = DebuggingAgent()

        await code_agent.initialize(guild)
        await debug_agent.initialize(guild)

        # Submit some tasks
        await guild.submit_work_request(
            "Create user authentication system",
            "Implement JWT-based authentication with login/logout endpoints",
            "high",
            ["code"],
            120,
        )

        await guild.submit_work_request(
            "Fix memory leak in data processor",
            "Investigate and fix memory leak causing performance issues",
            "urgent",
            ["debug"],
            90,
        )

        # Let agents work
        await asyncio.sleep(10)

        # Show agent status
        print("\n🤖 Agent Status:")
        print(json.dumps(code_agent.get_agent_status(), indent=2))
        print(json.dumps(debug_agent.get_agent_status(), indent=2))

        # Cleanup
        await code_agent.stop()
        await debug_agent.stop()
        await guild.stop()

    logger.info("🤖 AI Agent Interface Demonstration")
    asyncio.run(demo_ai_agent())
