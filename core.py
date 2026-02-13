"""
Guild Core - Central orchestration and coordination hub
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger

from .task_director import TaskDirector
from .agent_coordinator import AgentCoordinator
from .batch_orchestrator import BatchOrchestrator
from .communication_hub import CommunicationHub
from .workspace_director import WorkspaceDirector
from .model_manager import ModelManager
from .advanced.resource_aware_model_manager import ResourceAwareModelManager


@dataclass
class GuildConfig:
    """Configuration for Guild operations"""

    task_board_path: str = "guild/ACTIVE_TASKS.md"
    artifact_dir: str = "artifacts/guild"
    max_concurrent_tasks: int = 10
    batch_size: int = 20
    heartbeat_interval: int = 30
    enable_auto_batching: bool = True
    enable_workspace_monitoring: bool = True
    enable_model_management: bool = True
    lm_studio_host: str = "localhost"
    lm_studio_base_port: int = 1234
    max_parallel_models: int = 5

    # Resource-aware model management
    enable_resource_awareness: bool = True
    resource_check_interval: int = 10  # seconds
    cpu_threshold_high: float = 70.0  # % CPU usage to prefer remote
    memory_threshold_high: float = 75.0  # % Memory usage to prefer remote
    gpu_threshold_high: float = 80.0  # % GPU usage to prefer remote
    cost_optimization_enabled: bool = True
    fallback_timeout: int = 30  # seconds

    # Remote model endpoints
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""


class GuildCore:
    """
    Central Guild orchestration hub that coordinates all sub-components.

    The Guild Core acts as the unified interface for:
    - Task management and lifecycle
    - Agent coordination and handoff
    - Batch processing orchestration
    - Inter-module communication
    - Workspace and directory management
    """

    def __init__(self, config: Optional[GuildConfig] = None, hub: Optional[Any] = None):
        self.config = config or GuildConfig()
        self.hub = hub
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Initialize sub-components
        self.task_director = TaskDirector(self.config, self)
        self.agent_coordinator = AgentCoordinator(self.config, self)
        self.batch_orchestrator = BatchOrchestrator(self.config, self)
        self.communication_hub = CommunicationHub(self.config, self)
        self.workspace_director = WorkspaceDirector(self.config, self)
        self.model_manager = (
            ResourceAwareModelManager(self.config, self)
            if self.config.enable_model_management
            else None
        )

        logger.info("Guild Core initialized with unified sub-module architecture")

    async def start(self) -> None:
        """Start all Guild sub-components"""
        if self._running:
            return

        logger.info("Starting Guild Core...")
        self._running = True

        # Start sub-components in dependency order
        await self.communication_hub.start()
        await self.workspace_director.start()
        await self.task_director.start()
        await self.agent_coordinator.start()
        await self.batch_orchestrator.start()
        if self.model_manager:
            await self.model_manager.start()

        # Start heartbeat monitoring
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.success("Guild Core started successfully")

    async def stop(self) -> None:
        """Stop all Guild sub-components"""
        if not self._running:
            return

        logger.info("Stopping Guild Core...")
        self._running = False

        # Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Stop sub-components in reverse order
        if self.model_manager:
            await self.model_manager.stop()
        await self.batch_orchestrator.stop()
        await self.agent_coordinator.stop()
        await self.task_director.stop()
        await self.workspace_director.stop()
        await self.communication_hub.stop()

        logger.info("Guild Core stopped")

    async def _heartbeat_loop(self) -> None:
        """Periodic health monitoring and coordination"""
        while self._running:
            try:
                await self._perform_heartbeat()
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Guild heartbeat error: {e}")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _perform_heartbeat(self) -> None:
        """Perform periodic health checks and coordination"""
        # Check component health
        health_status = await self.get_health_status()

        # Trigger auto-batching if enabled
        if self.config.enable_auto_batching:
            await self.batch_orchestrator.check_auto_batch()

        # Workspace cleanup if enabled
        if self.config.enable_workspace_monitoring:
            await self.workspace_director.periodic_cleanup()

        # Agent coordination updates
        await self.agent_coordinator.update_agent_status()

        # Emit heartbeat event
        await self.communication_hub.emit_event(
            "guild.heartbeat",
            {
                "timestamp": asyncio.get_event_loop().time(),
                "health": health_status,
                "active_tasks": await self.task_director.get_active_count(),
                "active_agents": await self.agent_coordinator.get_active_count(),
            },
        )

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of all Guild components"""
        health = {
            "core": {"status": "healthy" if self._running else "stopped"},
            "task_director": await self.task_director.get_health(),
            "agent_coordinator": await self.agent_coordinator.get_health(),
            "batch_orchestrator": await self.batch_orchestrator.get_health(),
            "communication_hub": await self.communication_hub.get_health(),
            "workspace_director": await self.workspace_director.get_health(),
        }

        if self.model_manager:
            health["model_manager"] = await self.model_manager.get_health()

        return health

    # Unified API methods that delegate to appropriate sub-components

    async def claim_task(
        self, agent_id: str, task_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Claim a task through unified Guild interface"""
        return await self.task_director.claim_task(agent_id, task_id)

    async def complete_task(
        self, task_id: str, agent_id: str, result: Dict[str, Any]
    ) -> bool:
        """Complete a task through unified Guild interface"""
        return await self.task_director.complete_task(task_id, agent_id, result)

    async def register_agent(self, agent_id: str, capabilities: List[str]) -> bool:
        """Register an agent through unified Guild interface"""
        return await self.agent_coordinator.register_agent(agent_id, capabilities)

    async def submit_batch(
        self, task_ids: List[str], description: str
    ) -> Optional[str]:
        """Submit batch through unified Guild interface"""
        return await self.batch_orchestrator.submit_batch(task_ids, description)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast event through unified Guild interface"""
        await self.communication_hub.emit_event(event_type, data)

    # Model management methods (if model manager is enabled)

    async def load_model(self, model_id: str) -> bool:
        """Load a local language model"""
        if not self.model_manager:
            logger.warning("Model management not enabled")
            return False
        return await self.model_manager.load_model(model_id)

    async def unload_model(self, model_id: str) -> bool:
        """Unload a local language model"""
        if not self.model_manager:
            return False
        return await self.model_manager.unload_model(model_id)

    async def submit_parallel_inference(self, prompt: str, **kwargs) -> str:
        """Submit a prompt for parallel inference across multiple models"""
        if not self.model_manager:
            logger.warning("Model management not enabled")
            return ""
        return await self.model_manager.submit_parallel_task(prompt, **kwargs)

    async def get_inference_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a parallel inference task"""
        if not self.model_manager:
            return None
        return await self.model_manager.get_task_result(task_id)

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available local models"""
        if not self.model_manager:
            return {}
        return self.model_manager.get_available_models()

    def get_loaded_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of currently loaded models"""
        if not self.model_manager:
            return {}
        return self.model_manager.get_loaded_models()
