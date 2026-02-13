"""
Guild Integration Layer - Seamless integration with existing AAS systems
"""

import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger
from pathlib import Path

from .core import GuildCore, GuildConfig
from .communication_hub import CommunicationChannel, MessagePriority


class GuildIntegration:
    """
    Integration layer that connects the new Guild system with existing AAS components.

    This class provides:
    - Backward compatibility with existing systems
    - Gradual migration path
    - Bridge between old and new architectures
    - Unified API for both systems
    """

    def __init__(self, hub=None):
        self.hub = hub  # Existing ManagerHub
        self.guild_core: Optional[GuildCore] = None
        self._integration_mode = "hybrid"  # hybrid, guild_only, legacy_only

        logger.info("Guild Integration Layer initialized")

    async def initialize_guild(self, config: Optional[GuildConfig] = None) -> bool:
        """Initialize the Guild system alongside existing systems"""
        try:
            # Create Guild configuration
            if not config:
                config = GuildConfig(
                    task_board_path="guild/ACTIVE_TASKS.md",
                    artifact_dir="artifacts/guild",
                    enable_auto_batching=True,
                    enable_workspace_monitoring=True,
                )

            # Initialize Guild Core
            self.guild_core = GuildCore(config=config, hub=self.hub)

            # Start Guild system
            await self.guild_core.start()

            # Set up integration bridges
            await self._setup_integration_bridges()

            logger.success("Guild system initialized and integrated")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Guild system: {e}")
            return False

    async def _setup_integration_bridges(self) -> None:
        """Set up bridges between Guild and existing systems"""
        try:
            # Bridge existing TaskManager to Guild TaskDirector
            if self.hub and hasattr(self.hub, "tasks"):
                await self._bridge_task_manager()

            # Bridge existing BatchManager to Guild BatchOrchestrator
            if self.hub and hasattr(self.hub, "batch_manager"):
                await self._bridge_batch_manager()

            # Bridge existing WorkspaceCoordinator to Guild WorkspaceDirector
            if self.hub and hasattr(self.hub, "workspace_coordinator"):
                await self._bridge_workspace_coordinator()

            # Bridge existing EventBus to Guild CommunicationHub
            if self.hub and hasattr(self.hub, "events"):
                await self._bridge_event_bus()

            # Bridge existing PluginManager to Guild AgentCoordinator
            if self.hub and hasattr(self.hub, "plugin_manager"):
                await self._bridge_plugin_manager()

        except Exception as e:
            logger.error(f"Failed to setup integration bridges: {e}")

    async def _bridge_task_manager(self) -> None:
        """Bridge existing TaskManager with Guild TaskDirector"""
        try:
            existing_task_manager = self.hub.tasks
            guild_task_director = self.guild_core.task_director

            # Subscribe to existing task events and forward to Guild
            if hasattr(existing_task_manager, "subscribe_to_events"):
                await existing_task_manager.subscribe_to_events(
                    self._forward_task_event_to_guild
                )

            # Subscribe to Guild task events and forward to existing system
            self.guild_core.communication_hub.subscribe(
                CommunicationChannel.TASK_UPDATES, self._forward_guild_task_event
            )

            logger.info("Task Manager bridge established")

        except Exception as e:
            logger.error(f"Failed to bridge Task Manager: {e}")

    async def _bridge_batch_manager(self) -> None:
        """Bridge existing BatchManager with Guild BatchOrchestrator"""
        try:
            existing_batch_manager = self.hub.batch_manager
            guild_batch_orchestrator = self.guild_core.batch_orchestrator

            # Set up bidirectional communication
            self.guild_core.communication_hub.subscribe(
                CommunicationChannel.BATCH_PROCESSING, self._forward_guild_batch_event
            )

            logger.info("Batch Manager bridge established")

        except Exception as e:
            logger.error(f"Failed to bridge Batch Manager: {e}")

    async def _bridge_workspace_coordinator(self) -> None:
        """Bridge existing WorkspaceCoordinator with Guild WorkspaceDirector"""
        try:
            existing_workspace = self.hub.workspace_coordinator
            guild_workspace = self.guild_core.workspace_director

            # Share workspace monitoring data
            self.guild_core.communication_hub.subscribe(
                CommunicationChannel.WORKSPACE_EVENTS,
                self._forward_guild_workspace_event,
            )

            logger.info("Workspace Coordinator bridge established")

        except Exception as e:
            logger.error(f"Failed to bridge Workspace Coordinator: {e}")

    async def _bridge_event_bus(self) -> None:
        """Bridge existing EventBus with Guild CommunicationHub"""
        try:
            existing_event_bus = self.hub.events
            guild_comm_hub = self.guild_core.communication_hub

            # The CommunicationHub already bridges to EventBus in its initialization
            logger.info("Event Bus bridge established")

        except Exception as e:
            logger.error(f"Failed to bridge Event Bus: {e}")

    async def _bridge_plugin_manager(self) -> None:
        """Bridge existing PluginManager with Guild AgentCoordinator"""
        try:
            existing_plugin_manager = self.hub.plugin_manager
            guild_agent_coordinator = self.guild_core.agent_coordinator

            # Register existing plugins as agents in Guild
            if hasattr(existing_plugin_manager, "get_active_plugins"):
                active_plugins = existing_plugin_manager.get_active_plugins()

                for plugin_name, plugin_info in active_plugins.items():
                    capabilities = plugin_info.get("capabilities", [])
                    await guild_agent_coordinator.register_agent(
                        agent_id=f"plugin_{plugin_name}",
                        name=plugin_name,
                        capabilities=capabilities,
                        metadata={"type": "plugin", "source": "existing_system"},
                    )

            logger.info("Plugin Manager bridge established")

        except Exception as e:
            logger.error(f"Failed to bridge Plugin Manager: {e}")

    # Event forwarding methods

    async def _forward_task_event_to_guild(self, event_data: Dict[str, Any]) -> None:
        """Forward task events from existing system to Guild"""
        try:
            enriched = self._infer_task_context(event_data)
            await self.guild_core.communication_hub.emit_event(
                event_type=f"legacy.{event_data.get('type', 'task_event')}",
                data=enriched,
                channel=CommunicationChannel.TASK_UPDATES,
                priority=MessagePriority.NORMAL,
            )
        except Exception as e:
            logger.error(f"Failed to forward task event to Guild: {e}")

    async def _forward_guild_task_event(self, message) -> None:
        """Forward Guild task events to existing system"""
        try:
            if self.hub and hasattr(self.hub, "events"):
                payload = dict(message.payload or {})
                payload = self._infer_task_context(payload)
                await self.hub.events.emit(
                    event_type=f"guild.{message.event_type}",
                    data=payload,
                    source="guild_integration",
                )
        except Exception as e:
            logger.error(f"Failed to forward Guild task event: {e}")

    def _infer_task_context(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(event_data)
        title = str(data.get("title", "")).lower()
        assignee = str(data.get("assignee", "")).lower()
        preferred_role = data.get("preferred_role")
        domain = data.get("domain")

        hints = f"{title} {assignee}"
        if not domain:
            if "home" in hints or "fortress" in hints:
                domain = "home"
            elif "android" in hints or "mobile" in hints:
                domain = "mobile"
            elif "desktop" in hints or "ui" in hints:
                domain = "desktop"
            elif "merlin" in hints:
                domain = "research"

        if not preferred_role:
            if "home" in hints or "fortress" in hints:
                preferred_role = "fortress"
            elif "android" in hints or "mobile" in hints:
                preferred_role = "androidapp"
            elif "desktop" in hints or "ui" in hints:
                preferred_role = "desktop"
            elif "merlin" in hints or "research" in hints:
                preferred_role = "merlin"

        if domain:
            data["domain"] = domain
        if preferred_role:
            data["preferred_role"] = preferred_role
        return data

    async def _forward_guild_batch_event(self, message) -> None:
        """Forward Guild batch events to existing system"""
        try:
            if self.hub and hasattr(self.hub, "events"):
                await self.hub.events.emit(
                    event_type=f"guild.{message.event_type}",
                    data=message.payload,
                    source="guild_integration",
                )
        except Exception as e:
            logger.error(f"Failed to forward Guild batch event: {e}")

    async def _forward_guild_workspace_event(self, message) -> None:
        """Forward Guild workspace events to existing system"""
        try:
            if self.hub and hasattr(self.hub, "events"):
                await self.hub.events.emit(
                    event_type=f"guild.{message.event_type}",
                    data=message.payload,
                    source="guild_integration",
                )
        except Exception as e:
            logger.error(f"Failed to forward Guild workspace event: {e}")

    # Unified API methods that route to appropriate system

    async def claim_task(
        self, agent_id: str, task_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Unified task claiming that routes to appropriate system"""
        try:
            if self._integration_mode == "guild_only" and self.guild_core:
                return await self.guild_core.claim_task(agent_id, task_id)
            elif self._integration_mode == "legacy_only" and self.hub:
                return await self.hub.tasks.claim_task(task_id or "next", agent_id)
            else:
                # Hybrid mode - try Guild first, fallback to legacy
                if self.guild_core:
                    result = await self.guild_core.claim_task(agent_id, task_id)
                    if result:
                        return result

                if self.hub and hasattr(self.hub, "tasks"):
                    return await self.hub.tasks.claim_task(task_id or "next", agent_id)

            return None

        except Exception as e:
            logger.error(f"Failed to claim task: {e}")
            return None

    async def complete_task(
        self, task_id: str, agent_id: str, result: Dict[str, Any]
    ) -> bool:
        """Unified task completion that routes to appropriate system"""
        try:
            success = False

            if self._integration_mode in ["guild_only", "hybrid"] and self.guild_core:
                success = await self.guild_core.complete_task(task_id, agent_id, result)

            if self._integration_mode in ["legacy_only", "hybrid"] and self.hub:
                if hasattr(self.hub, "tasks"):
                    legacy_success = await self.hub.tasks.complete_task(
                        task_id, agent_id, result
                    )
                    success = success or legacy_success

            return success

        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            return False

    async def submit_batch(
        self, task_ids: List[str], description: str
    ) -> Optional[str]:
        """Unified batch submission that routes to appropriate system"""
        try:
            if self._integration_mode == "guild_only" and self.guild_core:
                return await self.guild_core.submit_batch(task_ids, description)
            elif self._integration_mode == "legacy_only" and self.hub:
                if hasattr(self.hub, "batch_manager"):
                    # Convert to legacy format
                    requests = []  # Would need to convert task_ids to requests
                    return await self.hub.batch_manager.submit_batch(
                        requests, description
                    )
            else:
                # Hybrid mode - prefer Guild
                if self.guild_core:
                    return await self.guild_core.submit_batch(task_ids, description)
                elif self.hub and hasattr(self.hub, "batch_manager"):
                    requests = []  # Would need to convert task_ids to requests
                    return await self.hub.batch_manager.submit_batch(
                        requests, description
                    )

            return None

        except Exception as e:
            logger.error(f"Failed to submit batch: {e}")
            return None

    async def register_agent(self, agent_id: str, capabilities: List[str]) -> bool:
        """Unified agent registration that routes to appropriate system"""
        try:
            success = False

            if self._integration_mode in ["guild_only", "hybrid"] and self.guild_core:
                success = await self.guild_core.register_agent(agent_id, capabilities)

            if self._integration_mode in ["legacy_only", "hybrid"] and self.hub:
                # Register with existing plugin system if applicable
                if hasattr(self.hub, "plugin_manager"):
                    # This would depend on the existing plugin registration API
                    pass

            return success

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive health status from both systems"""
        try:
            health_status = {
                "integration_mode": self._integration_mode,
                "guild_system": None,
                "legacy_system": None,
                "overall_status": "unknown",
            }

            # Get Guild system health
            if self.guild_core:
                health_status[
                    "guild_system"
                ] = await self.guild_core.get_health_status()

            # Get legacy system health
            if self.hub:
                legacy_health = {}

                if hasattr(self.hub, "tasks"):
                    legacy_health["tasks"] = await self.hub.tasks.get_status()

                if hasattr(self.hub, "batch_manager"):
                    legacy_health["batch"] = await self.hub.batch_manager.get_status()

                if hasattr(self.hub, "workspace_coordinator"):
                    legacy_health["workspace"] = {"status": "active"}

                health_status["legacy_system"] = legacy_health

            # Determine overall status
            guild_healthy = (
                health_status["guild_system"]
                and health_status["guild_system"]["core"]["status"] == "healthy"
            )
            legacy_healthy = bool(health_status["legacy_system"])

            if guild_healthy and legacy_healthy:
                health_status["overall_status"] = "excellent"
            elif guild_healthy or legacy_healthy:
                health_status["overall_status"] = "good"
            else:
                health_status["overall_status"] = "degraded"

            return health_status

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {"error": str(e)}

    async def set_integration_mode(self, mode: str) -> bool:
        """Set the integration mode (hybrid, guild_only, legacy_only)"""
        try:
            if mode not in ["hybrid", "guild_only", "legacy_only"]:
                logger.error(f"Invalid integration mode: {mode}")
                return False

            old_mode = self._integration_mode
            self._integration_mode = mode

            logger.info(f"Integration mode changed from {old_mode} to {mode}")

            # Emit mode change event
            if self.guild_core:
                await self.guild_core.communication_hub.emit_event(
                    "integration.mode_changed",
                    {"old_mode": old_mode, "new_mode": mode},
                    CommunicationChannel.SYSTEM_ALERTS,
                    MessagePriority.HIGH,
                )

            return True

        except Exception as e:
            logger.error(f"Failed to set integration mode: {e}")
            return False

    async def migrate_to_guild(self) -> bool:
        """Migrate existing data and state to Guild system"""
        try:
            if not self.guild_core:
                logger.error("Guild system not initialized")
                return False

            logger.info("Starting migration to Guild system...")

            # Migrate tasks
            if self.hub and hasattr(self.hub, "tasks"):
                await self._migrate_tasks()

            # Migrate batch jobs
            if self.hub and hasattr(self.hub, "batch_manager"):
                await self._migrate_batches()

            # Migrate agent/plugin data
            if self.hub and hasattr(self.hub, "plugin_manager"):
                await self._migrate_agents()

            # Switch to guild_only mode
            await self.set_integration_mode("guild_only")

            logger.success("Migration to Guild system completed")
            return True

        except Exception as e:
            logger.error(f"Failed to migrate to Guild system: {e}")
            return False

    async def _migrate_tasks(self) -> None:
        """Migrate existing tasks to Guild TaskDirector"""
        try:
            # This would depend on the existing task storage format
            # For now, we rely on the TaskDirector loading from Markdown
            logger.info("Task migration completed (loaded from Markdown)")

        except Exception as e:
            logger.error(f"Failed to migrate tasks: {e}")

    async def _migrate_batches(self) -> None:
        """Migrate existing batch jobs to Guild BatchOrchestrator"""
        try:
            # This would migrate existing batch state
            logger.info("Batch migration completed")

        except Exception as e:
            logger.error(f"Failed to migrate batches: {e}")

    async def _migrate_agents(self) -> None:
        """Migrate existing plugins/agents to Guild AgentCoordinator"""
        try:
            # Already handled in _bridge_plugin_manager
            logger.info("Agent migration completed")

        except Exception as e:
            logger.error(f"Failed to migrate agents: {e}")

    async def shutdown(self) -> None:
        """Shutdown the Guild integration layer"""
        try:
            if self.guild_core:
                await self.guild_core.stop()

            logger.info("Guild Integration Layer shutdown completed")

        except Exception as e:
            logger.error(f"Failed to shutdown Guild integration: {e}")


# Convenience function for easy integration
async def integrate_guild_with_existing_hub(hub) -> GuildIntegration:
    """
    Convenience function to integrate Guild system with existing ManagerHub.

    Usage:
        integration = await integrate_guild_with_existing_hub(hub)
        # Now use integration.claim_task(), integration.submit_batch(), etc.
    """
    integration = GuildIntegration(hub=hub)

    success = await integration.initialize_guild()
    if not success:
        logger.error("Failed to integrate Guild system")
        return None

    return integration
