"""
Hub Integration Example

This demonstrates how the AAS Hub can efficiently integrate with the Guild system
through the operational interface, providing clean task management without
mystical complexity getting in the way.
"""

import asyncio
from typing import Dict, Any, List
from loguru import logger
import json

# Import the operational interface
from ..interfaces.operational_interface import (
    GuildOperationalInterface,
    TaskPriority,
    AgentCapability,
    create_operational_guild,
)


class AASHubGuildIntegration:
    """
    Integration layer between AAS Hub and Guild system.

    This provides a clean, efficient interface for the hub to:
    - Submit development tasks
    - Track progress and completion
    - Manage AI agent assignments
    - Monitor system performance
    - Get intelligent recommendations
    """

    def __init__(self):
        self.guild: GuildOperationalInterface = None
        self.task_mapping: Dict[str, str] = {}  # hub_task_id -> guild_task_id
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def initialize(self, enable_mystical_background: bool = True):
        """Initialize the Guild integration"""

        logger.info("🔌 Initializing AAS Hub - Guild integration...")

        # Create operational guild
        self.guild = await create_operational_guild(enable_mystical_background)

        # Register additional specialized agents for AAS workflows
        await self._register_aas_agents()

        logger.info("✅ AAS Hub - Guild integration ready")

    async def _register_aas_agents(self):
        """Register AAS-specific agents"""

        # Register agents for common AAS tasks
        agents_to_register = [
            {
                "name": "AAS Code Review Agent",
                "capabilities": [AgentCapability.CODE_REVIEW, AgentCapability.ANALYSIS],
                "specialization": "AAS codebase review and quality assurance",
            },
            {
                "name": "AAS Test Automation Agent",
                "capabilities": [
                    AgentCapability.TESTING,
                    AgentCapability.CODE_GENERATION,
                ],
                "specialization": "Automated testing for AAS components",
            },
            {
                "name": "AAS Documentation Agent",
                "capabilities": [
                    AgentCapability.DOCUMENTATION,
                    AgentCapability.ANALYSIS,
                ],
                "specialization": "AAS system documentation and guides",
            },
            {
                "name": "AAS Integration Agent",
                "capabilities": [
                    AgentCapability.CODE_GENERATION,
                    AgentCapability.TESTING,
                ],
                "specialization": "Inter-module integration and API development",
            },
            {
                "name": "AAS Performance Agent",
                "capabilities": [
                    AgentCapability.OPTIMIZATION,
                    AgentCapability.ANALYSIS,
                ],
                "specialization": "AAS system performance optimization",
            },
        ]

        for agent_config in agents_to_register:
            await self.guild.register_agent(
                agent_config["name"],
                agent_config["capabilities"],
                agent_config["specialization"],
            )

        logger.info(f"🤖 Registered {len(agents_to_register)} AAS-specialized agents")

    # === HUB API METHODS ===

    async def submit_development_task(
        self, hub_task_id: str, task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit a development task from the hub"""

        # Extract task information
        title = task_data.get("title", "Development Task")
        description = task_data.get("description", "")
        priority = task_data.get("priority", "normal")
        task_type = task_data.get("type", "general")
        estimated_time = task_data.get("estimated_minutes", 60)

        # Map task type to required capabilities
        capabilities = self._map_task_type_to_capabilities(task_type)

        # Submit to guild
        result = await self.guild.submit_work_request(
            title=title,
            description=description,
            priority=priority,
            capabilities=capabilities,
            estimated_minutes=estimated_time,
        )

        # Store mapping
        guild_task_id = result["task_id"]
        self.task_mapping[hub_task_id] = guild_task_id

        logger.info(
            f"📝 Hub task {hub_task_id} submitted as Guild task {guild_task_id}"
        )

        return {
            "hub_task_id": hub_task_id,
            "guild_task_id": guild_task_id,
            "status": "submitted",
            "queue_position": result["queue_position"],
            "estimated_completion": result["estimated_completion"],
        }

    def _map_task_type_to_capabilities(self, task_type: str) -> List[str]:
        """Map AAS task types to agent capabilities"""

        type_mapping = {
            "code_generation": ["code"],
            "code_review": ["review", "analyze"],
            "bug_fix": ["debug", "test"],
            "optimization": ["optimize", "analyze"],
            "testing": ["test", "code"],
            "documentation": ["docs", "analyze"],
            "integration": ["code", "test"],
            "research": ["research", "analyze"],
            "refactoring": ["code", "review", "test"],
            "ui_automation": ["code", "test"],
            "api_development": ["code", "docs", "test"],
        }

        return type_mapping.get(task_type, ["code"])

    async def check_task_status(self, hub_task_id: str) -> Dict[str, Any]:
        """Check status of a hub task"""

        if hub_task_id not in self.task_mapping:
            return {"error": "Task not found"}

        guild_task_id = self.task_mapping[hub_task_id]
        guild_status = await self.guild.check_work_status(guild_task_id)

        # Convert to hub-friendly format
        return {
            "hub_task_id": hub_task_id,
            "status": guild_status.get("status", "unknown"),
            "assigned_agent": guild_status.get("agent_name"),
            "created_at": guild_status.get("created_at"),
            "completed_at": guild_status.get("completed_at"),
            "title": guild_status.get("title"),
        }

    async def get_system_dashboard(self) -> Dict[str, Any]:
        """Get system dashboard data for the hub"""

        guild_status = await self.guild.get_system_status()

        # Create hub-friendly dashboard
        dashboard = {
            "system_health": "healthy" if guild_status["system_running"] else "offline",
            "task_summary": {
                "total_tasks": guild_status["tasks"]["total"],
                "pending": guild_status["tasks"]["pending"],
                "active": guild_status["tasks"]["active"],
                "completed": guild_status["tasks"]["completed"],
                "queue_length": guild_status["tasks"]["queue_length"],
            },
            "agent_summary": {
                "total_agents": guild_status["agents"]["total"],
                "available": guild_status["agents"]["available"],
                "busy": guild_status["agents"]["busy"],
            },
            "performance": {
                "total_completed": guild_status["performance"]["total_completed"],
                "average_completion_time": f"{guild_status['performance']['average_completion_time']:.1f} minutes",
                "success_rate": f"{guild_status['performance']['success_rate'] * 100:.1f}%",
            },
            "resource_usage": {
                "cpu": f"{guild_status['resources']['cpu_usage']:.1f}%",
                "memory": f"{guild_status['resources']['memory_usage']:.1f}%",
                "model_routing": (
                    "local" if guild_status["resources"]["cpu_usage"] < 70 else "remote"
                ),
            },
        }

        # Add mystical status if available (for engagement metrics)
        if guild_status.get("mystical_status"):
            mystical = guild_status["mystical_status"]
            dashboard["engagement_metrics"] = {
                "magical_agents": mystical["magical_agents"],
                "active_enhancements": mystical["active_spells"],
                "system_energy": f"{mystical['guild_mana_pool']:.0f}/1000",
                "performance_dragons": mystical["digital_dragons"],
            }

        return dashboard

    async def get_agent_recommendations(
        self, task_type: str, description: str = ""
    ) -> List[Dict[str, Any]]:
        """Get agent recommendations for a specific task type"""

        # Get available agents from guild
        capabilities = self._map_task_type_to_capabilities(task_type)
        capability_enums = []

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

        for cap in capabilities:
            if cap in capability_map:
                capability_enums.append(capability_map[cap])

        available_agents = await self.guild.get_available_agents(capability_enums)

        # Format for hub display
        recommendations = []
        for agent in available_agents[:5]:  # Top 5 recommendations
            recommendations.append(
                {
                    "agent_id": agent.id,
                    "name": agent.name,
                    "specialization": agent.specialization or "General AI Agent",
                    "current_load": f"{agent.current_load * 100:.0f}%",
                    "performance_rating": f"{agent.performance_rating * 100:.0f}%",
                    "capabilities": [cap.value for cap in agent.capabilities],
                    "availability": "available" if agent.available else "busy",
                }
            )

        return recommendations

    async def request_priority_assignment(
        self, hub_task_id: str, agent_preference: str = None
    ) -> Dict[str, Any]:
        """Request priority assignment for urgent tasks"""

        if hub_task_id not in self.task_mapping:
            return {"error": "Task not found"}

        guild_task_id = self.task_mapping[hub_task_id]

        # Update task priority to urgent
        task = await self.guild.get_task(guild_task_id)
        if task:
            task.priority = TaskPriority.URGENT

            # Try to assign immediately
            if agent_preference:
                # Find agent by name
                for agent_id, agent in self.guild.agents.items():
                    if agent_preference.lower() in agent.name.lower():
                        success = await self.guild.assign_task_to_agent(
                            guild_task_id, agent_id
                        )
                        if success:
                            return {
                                "status": "assigned",
                                "assigned_agent": agent.name,
                                "message": "Task assigned to preferred agent",
                            }

            # Auto-assign to best available agent
            success = await self.guild.auto_assign_task(guild_task_id)
            if success:
                return {
                    "status": "assigned",
                    "message": "Task assigned to best available agent",
                }
            else:
                return {
                    "status": "queued",
                    "message": "Task marked as urgent, will be assigned when agent becomes available",
                }

        return {"error": "Could not update task priority"}

    # === BATCH OPERATIONS ===

    async def submit_batch_tasks(
        self, batch_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Submit multiple tasks as a batch"""

        results = []
        batch_id = f"batch_{len(self.active_sessions) + 1:04d}"

        for i, task_data in enumerate(batch_data):
            hub_task_id = f"{batch_id}_task_{i+1:03d}"

            try:
                result = await self.submit_development_task(hub_task_id, task_data)
                results.append(result)
            except Exception as e:
                results.append({"hub_task_id": hub_task_id, "error": str(e)})

        # Store batch session
        self.active_sessions[batch_id] = {
            "created_at": asyncio.get_event_loop().time(),
            "task_count": len(batch_data),
            "results": results,
        }

        return {
            "batch_id": batch_id,
            "submitted_tasks": len(results),
            "successful_submissions": len([r for r in results if "error" not in r]),
            "results": results,
        }

    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of a batch operation"""

        if batch_id not in self.active_sessions:
            return {"error": "Batch not found"}

        batch_session = self.active_sessions[batch_id]

        # Get current status of all tasks in batch
        task_statuses = []
        for result in batch_session["results"]:
            if "hub_task_id" in result and "error" not in result:
                status = await self.check_task_status(result["hub_task_id"])
                task_statuses.append(status)

        # Calculate batch statistics
        completed = len([s for s in task_statuses if s.get("status") == "completed"])
        active = len(
            [s for s in task_statuses if s.get("status") in ["assigned", "in_progress"]]
        )
        pending = len([s for s in task_statuses if s.get("status") == "pending"])

        return {
            "batch_id": batch_id,
            "total_tasks": batch_session["task_count"],
            "completed": completed,
            "active": active,
            "pending": pending,
            "completion_percentage": (
                (completed / batch_session["task_count"]) * 100
                if batch_session["task_count"] > 0
                else 0
            ),
            "task_details": task_statuses,
        }

    # === MONITORING AND ANALYTICS ===

    async def get_performance_analytics(
        self, time_period: str = "24h"
    ) -> Dict[str, Any]:
        """Get performance analytics for the specified time period"""

        guild_status = await self.guild.get_system_status()

        # For now, return current performance data
        # In a real implementation, this would query historical data

        return {
            "time_period": time_period,
            "task_completion": {
                "total_completed": guild_status["performance"]["total_completed"],
                "average_completion_time": guild_status["performance"][
                    "average_completion_time"
                ],
                "success_rate": guild_status["performance"]["success_rate"],
            },
            "agent_performance": guild_status["performance"]["agent_performance"],
            "resource_efficiency": {
                "average_cpu_usage": guild_status["resources"]["cpu_usage"],
                "average_memory_usage": guild_status["resources"]["memory_usage"],
                "local_vs_remote_ratio": "70/30",  # Placeholder
            },
            "system_health": {
                "uptime": "99.9%",  # Placeholder
                "error_rate": "0.1%",  # Placeholder
                "response_time": "< 1s",  # Placeholder
            },
        }

    async def shutdown(self):
        """Shutdown the integration"""

        logger.info("🔌 Shutting down AAS Hub - Guild integration...")

        if self.guild:
            await self.guild.stop()

        logger.info("✅ AAS Hub - Guild integration shutdown complete")


# === EXAMPLE USAGE ===


async def demonstrate_hub_integration():
    """Demonstrate how the AAS Hub would use the Guild integration"""

    logger.info("🚀 AAS Hub - Guild Integration Demonstration")
    logger.info("=" * 50)

    # Initialize integration
    hub_integration = AASHubGuildIntegration()
    await hub_integration.initialize(enable_mystical_background=True)

    try:
        # Example 1: Submit individual development tasks
        logger.info("\n📝 Example 1: Submitting individual tasks")

        tasks_to_submit = [
            {
                "title": "Implement user authentication API",
                "description": "Create REST API endpoints for user login/logout with JWT tokens",
                "type": "api_development",
                "priority": "high",
                "estimated_minutes": 120,
            },
            {
                "title": "Fix memory leak in data processing module",
                "description": "Investigate and fix memory leak causing performance degradation",
                "type": "bug_fix",
                "priority": "urgent",
                "estimated_minutes": 90,
            },
            {
                "title": "Add unit tests for payment processing",
                "description": "Create comprehensive unit tests for payment module",
                "type": "testing",
                "priority": "normal",
                "estimated_minutes": 180,
            },
        ]

        submitted_tasks = []
        for i, task_data in enumerate(tasks_to_submit):
            hub_task_id = f"hub_task_{i+1:03d}"
            result = await hub_integration.submit_development_task(
                hub_task_id, task_data
            )
            submitted_tasks.append(hub_task_id)
            logger.info(f"   ✅ Submitted: {task_data['title']}")

        # Example 2: Check system dashboard
        logger.info("\n📊 Example 2: System dashboard")
        dashboard = await hub_integration.get_system_dashboard()
        logger.info(f"   System Health: {dashboard['system_health']}")
        logger.info(f"   Active Tasks: {dashboard['task_summary']['active']}")
        logger.info(f"   Available Agents: {dashboard['agent_summary']['available']}")
        logger.info(f"   CPU Usage: {dashboard['resource_usage']['cpu']}")

        # Example 3: Get agent recommendations
        logger.info("\n🤖 Example 3: Agent recommendations")
        recommendations = await hub_integration.get_agent_recommendations(
            "optimization"
        )
        for rec in recommendations[:3]:
            logger.info(
                f"   Agent: {rec['name']} - Load: {rec['current_load']} - Rating: {rec['performance_rating']}"
            )

        # Example 4: Batch task submission
        logger.info("\n📦 Example 4: Batch task submission")
        batch_tasks = [
            {
                "title": "Refactor database queries",
                "type": "optimization",
                "priority": "normal",
            },
            {
                "title": "Update API documentation",
                "type": "documentation",
                "priority": "low",
            },
            {
                "title": "Implement caching layer",
                "type": "code_generation",
                "priority": "normal",
            },
        ]

        batch_result = await hub_integration.submit_batch_tasks(batch_tasks)
        logger.info(f"   Batch submitted: {batch_result['batch_id']}")
        logger.info(
            f"   Successful submissions: {batch_result['successful_submissions']}/{batch_result['submitted_tasks']}"
        )

        # Example 5: Monitor task progress
        logger.info("\n📈 Example 5: Task status monitoring")
        for task_id in submitted_tasks[:2]:  # Check first 2 tasks
            status = await hub_integration.check_task_status(task_id)
            logger.info(
                f"   Task {task_id}: {status['status']} - Agent: {status.get('assigned_agent', 'None')}"
            )

        # Example 6: Performance analytics
        logger.info("\n📊 Example 6: Performance analytics")
        analytics = await hub_integration.get_performance_analytics()
        logger.info(
            f"   Completed Tasks: {analytics['task_completion']['total_completed']}"
        )
        logger.info(
            f"   Average Completion Time: {analytics['task_completion']['average_completion_time']:.1f} minutes"
        )
        logger.info(
            f"   Success Rate: {analytics['task_completion']['success_rate'] * 100:.1f}%"
        )

        logger.info("\n🎉 Hub integration demonstration complete!")

    finally:
        # Cleanup
        await hub_integration.shutdown()


if __name__ == "__main__":
    asyncio.run(demonstrate_hub_integration())
