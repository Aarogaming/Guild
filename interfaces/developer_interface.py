"""
Developer Interface for Guild System

This provides a clean, developer-friendly interface for individual developers
to interact with the Guild system through CLI commands, IDE integration,
or direct API calls.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, cast
from dataclasses import asdict
from loguru import logger
import argparse
from pathlib import Path

from .operational_interface import (
    GuildOperationalInterface,
    TaskPriority,
    AgentCapability,
    create_operational_guild,
)


def _normalize_status_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", "_")
    return normalized


def _format_priority(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _coerce_config_value(value: str, current_value: Any) -> Any:
    if isinstance(current_value, bool):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
        raise ValueError("Expected boolean value")
    if isinstance(current_value, int):
        return int(value)
    return value


class DeveloperGuildInterface:
    """
    Developer-friendly interface for Guild system interaction.

    Provides:
    - Simple CLI commands for common operations
    - IDE integration helpers
    - Personal task management
    - Development workflow optimization
    - Performance insights
    """

    def __init__(self):
        self.guild: GuildOperationalInterface = cast(GuildOperationalInterface, None)
        self.config_file = Path.home() / ".guild_config.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load developer configuration"""

        default_config = {
            "developer_name": "Developer",
            "preferred_agents": [],
            "default_priority": "normal",
            "enable_mystical_features": True,
            "auto_assign_tasks": True,
            "notification_preferences": {
                "task_completion": True,
                "agent_assignments": True,
                "system_alerts": False,
            },
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"Could not load config: {e}")

        return default_config

    def _save_config(self):
        """Save developer configuration"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save config: {e}")

    async def initialize(self):
        """Initialize the developer interface"""

        logger.info(
            f"👨‍💻 Initializing Guild interface for {self.config['developer_name']}"
        )

        # Create operational guild
        self.guild = await create_operational_guild(
            enable_mystical=self.config["enable_mystical_features"]
        )

        logger.info("✅ Developer Guild interface ready")

    # === TASK MANAGEMENT ===

    async def create_task(
        self,
        title: str,
        description: str = "",
        priority: Optional[str] = None,
        task_type: str = "general",
        estimated_minutes: Optional[int] = None,
        execution_mode: Optional[str] = None,
        execute_gate: bool = False,
    ) -> str:
        """Create a new development task"""

        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")

        # Use config defaults if not specified
        if priority is None:
            priority = self.config["default_priority"]
        priority_value = str(priority)

        allowed_priorities = {"low", "normal", "high", "urgent", "critical"}
        if priority_value.lower() not in allowed_priorities:
            logger.warning(f"Unknown priority '{priority_value}', using default")
            priority_value = self.config["default_priority"]

        if estimated_minutes is None:
            estimated_minutes = 60
        if estimated_minutes <= 0:
            logger.warning("Estimated minutes must be positive; using 60")
            estimated_minutes = 60

        # Map task type to capabilities
        type_capabilities = {
            "code": ["code"],
            "review": ["review"],
            "test": ["test"],
            "debug": ["debug"],
            "optimize": ["optimize"],
            "docs": ["docs"],
            "research": ["research"],
            "refactor": ["code", "review"],
        }

        capabilities = type_capabilities.get(task_type, ["code"])
        if task_type not in type_capabilities:
            logger.warning(f"Unknown task type '{task_type}', defaulting to code")

        # Submit task
        result = await self.guild.submit_work_request(
            title=title,
            description=description,
            priority=priority_value,
            capabilities=capabilities,
            estimated_minutes=estimated_minutes,
            execution_mode=execution_mode or "automatic",
            execute_gate=execute_gate,
        )

        task_id = result["task_id"]

        print(f"✅ Task created: {title}")
        print(f"   Task ID: {task_id}")
        print(f"   Priority: {priority_value}")
        if execution_mode:
            print(f"   Mode: {execution_mode}")
        if execute_gate:
            print("   Execute gate: required")
        print(f"   Queue position: {result['queue_position']}")
        print(f"   Estimated completion: {result['estimated_completion']}")

        return task_id

    async def list_tasks(
        self, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List tasks with optional status filter"""
        tasks = await self.guild.list_tasks(status_filter)
        task_dicts = [asdict(task) for task in tasks]
        task_dicts.sort(key=lambda t: t["created_at"], reverse=True)
        return task_dicts

    async def show_task(self, task_id: str):
        """Show detailed task information"""

        status = await self.guild.check_work_status(task_id)

        if "error" in status:
            print(f"❌ {status['error']}")
            return

        print(f"📋 Task Details: {task_id}")
        print(f"   Title: {status['title']}")
        print(f"   Status: {status['status']}")
        print(f"   Created: {status['created_at']}")

        if status.get("assigned_agent"):
            print(f"   Assigned Agent: {status['agent_name']}")

        if status.get("completed_at"):
            print(f"   Completed: {status['completed_at']}")

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""

        task = await self.guild.get_task(task_id)
        if not task:
            print(f"❌ Task {task_id} not found")
            return False

        if task.status.value not in {"queued", "blocked"}:
            print(f"❌ Cannot cancel task in status: {task.status.value}")
            return False

        await self.guild.update_task_status(task_id, "cancelled")

        print(f"✅ Task {task_id} cancelled")
        return True

    async def start_execution(self, task_id: str, agent_id: str) -> bool:
        """Start execution for a task after execute approval."""
        success = await self.guild.start_execution(task_id, agent_id)
        if success:
            print(f"✅ Execution started for {task_id} by {agent_id}")
        else:
            print(f"❌ Unable to start execution for {task_id}")
        return success

    # === AGENT MANAGEMENT ===

    async def list_agents(self, available_only: bool = False):
        """List available agents"""

        agents = await self.guild.list_agents(available_only=available_only)

        print(f"🤖 {'Available ' if available_only else ''}Agents:")

        for agent in agents:
            status_icon = "🟢" if agent.available else "🔴"
            load_bar = "█" * int(agent.current_load * 10) + "░" * (
                10 - int(agent.current_load * 10)
            )

            print(f"   {status_icon} {agent.name}")
            print(f"      Load: [{load_bar}] {agent.current_load * 100:.0f}%")
            print(f"      Rating: {agent.performance_rating * 100:.0f}%")
            print(
                f"      Capabilities: {', '.join([cap.value for cap in agent.capabilities])}"
            )
            if agent.specialization:
                print(f"      Specialization: {agent.specialization}")
            print()

    async def get_recommendations(self, task_type: str = "code"):
        """Get agent recommendations for a task type"""

        # Map task type to capabilities
        type_mapping = {
            "code": [AgentCapability.CODE_GENERATION],
            "review": [AgentCapability.CODE_REVIEW],
            "test": [AgentCapability.TESTING],
            "debug": [AgentCapability.DEBUGGING],
            "optimize": [AgentCapability.OPTIMIZATION],
            "docs": [AgentCapability.DOCUMENTATION],
        }

        capabilities = type_mapping.get(task_type, [AgentCapability.CODE_GENERATION])
        agents = await self.guild.get_available_agents(capabilities)

        print(f"🎯 Recommended agents for {task_type} tasks:")

        for i, agent in enumerate(agents[:5], 1):
            print(f"   {i}. {agent.name}")
            print(
                f"      Load: {agent.current_load * 100:.0f}% | Rating: {agent.performance_rating * 100:.0f}%"
            )
            if agent.specialization:
                print(f"      Specialization: {agent.specialization}")
            print()

    # === WORKFLOW HELPERS ===

    async def quick_code_task(self, description: str, priority: str = "normal") -> str:
        """Quick helper for creating code generation tasks"""

        return await self.create_task(
            title=f"Code: {description[:50]}...",
            description=description,
            priority=priority,
            task_type="code",
            estimated_minutes=45,
        )

    async def quick_review_task(self, file_path: str, priority: str = "normal") -> str:
        """Quick helper for creating code review tasks"""

        return await self.create_task(
            title=f"Review: {Path(file_path).name}",
            description=f"Code review for {file_path}",
            priority=priority,
            task_type="review",
            estimated_minutes=30,
        )

    async def quick_debug_task(
        self, issue_description: str, priority: str = "high"
    ) -> str:
        """Quick helper for creating debug tasks"""

        return await self.create_task(
            title=f"Debug: {issue_description[:50]}...",
            description=issue_description,
            priority=priority,
            task_type="debug",
            estimated_minutes=90,
        )

    async def batch_file_review(
        self, file_paths: List[str], priority: str = "normal"
    ) -> List[str]:
        """Create review tasks for multiple files"""

        task_ids = []

        for file_path in file_paths:
            task_id = await self.quick_review_task(file_path, priority)
            task_ids.append(task_id)

        print(f"✅ Created {len(task_ids)} review tasks")
        return task_ids

    # === STATUS AND MONITORING ===

    async def show_dashboard(self):
        """Show developer dashboard"""

        status = await self.guild.get_system_status()

        print("📊 Guild System Dashboard")
        print("=" * 40)

        # System status
        health_icon = "🟢" if status["system_running"] else "🔴"
        print(
            f"{health_icon} System Status: {'Online' if status['system_running'] else 'Offline'}"
        )

        # Task summary
        tasks = status["tasks"]
        print(f"\n📋 Tasks:")
        print(f"   Total: {tasks['total']}")
        print(f"   Pending: {tasks['pending']}")
        print(f"   Active: {tasks['active']}")
        print(f"   Completed: {tasks['completed']}")
        print(f"   Queue Length: {tasks['queue_length']}")

        # Agent summary
        agents = status["agents"]
        print(f"\n🤖 Agents:")
        print(f"   Total: {agents['total']}")
        print(f"   Available: {agents['available']}")
        print(f"   Busy: {agents['busy']}")

        # Performance
        perf = status["performance"]
        print(f"\n📈 Performance:")
        print(f"   Completed Tasks: {perf['total_completed']}")
        print(f"   Avg Completion Time: {perf['average_completion_time']:.1f} minutes")
        print(f"   Success Rate: {perf['success_rate'] * 100:.1f}%")

        # Resource usage
        resources = status["resources"]
        print(f"\n💻 Resources:")
        print(f"   CPU: {resources['cpu_usage']:.1f}%")
        print(f"   Memory: {resources['memory_usage']:.1f}%")
        print(
            f"   Model Routing: {'Local' if resources['cpu_usage'] < 70 else 'Remote'}"
        )

        # Mystical status (if enabled)
        if status.get("mystical_status") and self.config["enable_mystical_features"]:
            mystical = status["mystical_status"]
            print(f"\n✨ Mystical Enhancements:")
            print(f"   Magical Agents: {mystical['magical_agents']}")
            print(f"   Guild Mana: {mystical['guild_mana_pool']:.0f}/1000")
            print(f"   Active Spells: {mystical['active_spells']}")
            print(f"   Digital Dragons: {mystical['digital_dragons']}")

    async def show_my_tasks(self):
        """Show tasks relevant to this developer"""

        # For now, show recent tasks
        # In a real implementation, this would filter by developer

        recent_tasks = await self.list_tasks()
        recent_tasks = recent_tasks[:10]  # Last 10 tasks

        print(f"📋 Your Recent Tasks:")
        print("-" * 60)

        for task in recent_tasks:
            status_value = (
                task["status"].value
                if hasattr(task["status"], "value")
                else task["status"]
            )
            status_icon = {
                "queued": "⏳",
                "blocked": "🚫",
                "in_progress": "⚡",
                "done": "✅",
                "failed": "❌",
                "cancelled": "❌",
            }.get(status_value, "❓")

            print(f"{status_icon} {task['title'][:50]}")
            print(
                f"   ID: {task['id']} | Status: {status_value} | Priority: {_format_priority(task['priority'])}"
            )
            print()

    # === CONFIGURATION ===

    async def configure(self, key: str, value: Any):
        """Update configuration"""

        if key in self.config:
            old_value = self.config[key]
            if isinstance(value, str):
                try:
                    value = _coerce_config_value(value, old_value)
                except ValueError as exc:
                    print(f"❌ Invalid value for {key}: {exc}")
                    return
            self.config[key] = value
            self._save_config()

            print(f"✅ Configuration updated:")
            print(f"   {key}: {old_value} → {value}")
        else:
            print(f"❌ Unknown configuration key: {key}")

    async def show_config(self):
        """Show current configuration"""

        print("⚙️ Guild Configuration:")
        print("-" * 30)

        for key, value in self.config.items():
            print(f"   {key}: {value}")

    async def shutdown(self):
        """Shutdown the developer interface"""

        if self.guild:
            await self.guild.stop()

        logger.info("✅ Developer Guild interface shutdown")

    # === DEVLIBRARY EVALUATION ===

    async def evaluate_devlibrary(
        self,
        workspace_path: str,
        analyzers: Optional[List[str]],
        output_format: str,
        output_path: Optional[str],
        quick_mode: bool,
        include_tasks: bool,
        summary_only: bool,
    ) -> int:
        """Run the DevLibrary evaluator through the Guild interface."""
        from core.managers import ManagerHub
        from guild.devlibrary_evaluator.cli import DevLibraryEvaluatorCLI

        hub = ManagerHub.create()
        evaluator_cli = DevLibraryEvaluatorCLI(hub)
        return await evaluator_cli.run_evaluation(
            workspace_path=workspace_path,
            analyzers=analyzers,
            output_format=output_format,
            output_path=output_path,
            quick_mode=quick_mode,
            include_tasks=include_tasks,
            summary_only=summary_only,
        )


# === CLI INTERFACE ===


class GuildCLI:
    """Command-line interface for the Guild system"""

    def __init__(self):
        self.interface = DeveloperGuildInterface()

    async def run_command(self, args):
        """Run a CLI command"""

        await self.interface.initialize()

        try:
            if args.command == "create":
                await self.interface.create_task(
                    title=args.title,
                    description=args.description or "",
                    priority=args.priority,
                    task_type=args.type,
                    estimated_minutes=args.time,
                    execution_mode=args.mode,
                    execute_gate=args.execute_gate,
                )

            elif args.command == "list":
                tasks = await self.interface.list_tasks(args.status)

                print(f"📋 Tasks ({args.status or 'all'}):")
                print("-" * 60)

                for task in tasks[:20]:  # Show last 20
                    status_value = (
                        task["status"].value
                        if hasattr(task["status"], "value")
                        else task["status"]
                    )
                    status_icon = {
                        "queued": "⏳",
                        "blocked": "🚫",
                        "in_progress": "⚡",
                        "done": "✅",
                        "failed": "❌",
                        "cancelled": "❌",
                    }.get(status_value, "❓")

                    print(f"{status_icon} {task['title'][:45]}")
                    print(
                        f"   ID: {task['id']} | {status_value} | {_format_priority(task['priority'])}"
                    )
                    print()

            elif args.command == "show":
                await self.interface.show_task(args.task_id)

            elif args.command == "cancel":
                await self.interface.cancel_task(args.task_id)

            elif args.command == "execute":
                await self.interface.start_execution(args.task_id, args.agent)

            elif args.command == "agents":
                await self.interface.list_agents(args.available)

            elif args.command == "recommend":
                await self.interface.get_recommendations(args.type)

            elif args.command == "dashboard":
                await self.interface.show_dashboard()

            elif args.command == "mytasks":
                await self.interface.show_my_tasks()

            elif args.command == "config":
                if args.key and args.value:
                    await self.interface.configure(args.key, args.value)
                else:
                    await self.interface.show_config()

            elif args.command == "evaluate":
                analyzers = None
                if args.analyzers:
                    analyzers = [
                        a.strip() for a in args.analyzers.split(",") if a.strip()
                    ]
                await self.interface.evaluate_devlibrary(
                    workspace_path=args.workspace,
                    analyzers=analyzers,
                    output_format=args.format,
                    output_path=args.output,
                    quick_mode=args.quick,
                    include_tasks=not args.no_tasks,
                    summary_only=args.summary_only,
                )

            elif args.command == "quick":
                if args.type == "code":
                    await self.interface.quick_code_task(
                        args.description, args.priority
                    )
                elif args.type == "review":
                    file_path = args.file or args.description
                    if not file_path:
                        print("❌ File path required for review tasks")
                        return
                    await self.interface.quick_review_task(file_path, args.priority)
                elif args.type == "debug":
                    await self.interface.quick_debug_task(
                        args.description, args.priority
                    )

        finally:
            await self.interface.shutdown()


def create_cli_parser():
    """Create CLI argument parser"""

    parser = argparse.ArgumentParser(description="Guild System Developer Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create task
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("title", help="Task title")
    create_parser.add_argument("-d", "--description", help="Task description")
    create_parser.add_argument(
        "-p",
        "--priority",
        default="normal",
        choices=["low", "normal", "high", "urgent", "critical"],
    )
    create_parser.add_argument(
        "-t",
        "--type",
        default="code",
        choices=["code", "review", "test", "debug", "optimize", "docs"],
    )
    create_parser.add_argument("--time", type=int, default=60, help="Estimated minutes")
    create_parser.add_argument(
        "--mode",
        default="automatic",
        choices=["automatic", "semi-automatic", "manual", "agent-assisted"],
        help="Execution mode",
    )
    create_parser.add_argument(
        "--execute-gate",
        action="store_true",
        help="Require execute approval gate",
    )

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("-s", "--status", help="Filter by status")

    # Show task
    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("task_id", help="Task ID")

    # Cancel task
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a task")
    cancel_parser.add_argument("task_id", help="Task ID")

    # Execute task
    execute_parser = subparsers.add_parser("execute", help="Start task execution")
    execute_parser.add_argument("task_id", help="Task ID")
    execute_parser.add_argument(
        "--agent",
        default="Developer",
        help="Agent ID starting execution",
    )

    # List agents
    agents_parser = subparsers.add_parser("agents", help="List agents")
    agents_parser.add_argument(
        "-a", "--available", action="store_true", help="Available only"
    )

    # Get recommendations
    recommend_parser = subparsers.add_parser(
        "recommend", help="Get agent recommendations"
    )
    recommend_parser.add_argument("-t", "--type", default="code", help="Task type")

    # Dashboard
    subparsers.add_parser("dashboard", help="Show system dashboard")

    # My tasks
    subparsers.add_parser("mytasks", help="Show your recent tasks")

    # Configuration
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("-k", "--key", help="Configuration key")
    config_parser.add_argument("-v", "--value", help="Configuration value")

    # Quick commands
    quick_parser = subparsers.add_parser("quick", help="Quick task creation")
    quick_parser.add_argument("type", choices=["code", "review", "debug"])
    quick_parser.add_argument(
        "description", help="Task description (or file path for review)"
    )
    quick_parser.add_argument("-f", "--file", help="File path (for review)")
    quick_parser.add_argument("-p", "--priority", default="normal")

    # DevLibrary evaluation
    eval_parser = subparsers.add_parser("evaluate", help="Run DevLibrary evaluation")
    eval_parser.add_argument("--workspace", default=".", help="Workspace path")
    eval_parser.add_argument(
        "--analyzers",
        help="Comma-separated analyzer keys (architecture,feature_gaps,...)",
    )
    eval_parser.add_argument(
        "--format",
        default="markdown",
        choices=["markdown", "md", "html", "json"],
        help="Output format",
    )
    eval_parser.add_argument("--output", help="Output path")
    eval_parser.add_argument("--quick", action="store_true")
    eval_parser.add_argument("--summary-only", action="store_true")
    eval_parser.add_argument("--no-tasks", action="store_true")

    return parser


async def main():
    """Main CLI entry point"""

    parser = create_cli_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = GuildCLI()
    await cli.run_command(args)


if __name__ == "__main__":
    asyncio.run(main())
