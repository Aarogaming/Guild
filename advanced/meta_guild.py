"""
Meta Guild - A Guild system that manages other Guild systems

This is where we completely lose our minds and create a Guild that manages Guilds.
Because if one level of abstraction is good, infinite levels must be better!
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from datetime import datetime, timezone
import json
import uuid
from pathlib import Path

from ..core import GuildCore, GuildConfig
from .neural_orchestrator import NeuralOrchestrator, OrchestrationStrategy


class GuildTier(Enum):
    """Different tiers of Guild systems"""

    NANO = "nano"  # Single-purpose micro-guilds
    MICRO = "micro"  # Small specialized guilds
    STANDARD = "standard"  # Regular guild systems
    MACRO = "macro"  # Large enterprise guilds
    MEGA = "mega"  # Massive distributed guilds
    META = "meta"  # Guilds that manage other guilds
    OMEGA = "omega"  # The guild to end all guilds


class GuildPersonality(Enum):
    """Because Guild systems need personalities too"""

    EFFICIENT = "efficient"
    CREATIVE = "creative"
    COLLABORATIVE = "collaborative"
    COMPETITIVE = "competitive"
    PERFECTIONIST = "perfectionist"
    CHAOTIC = "chaotic"
    PHILOSOPHICAL = "philosophical"


@dataclass
class GuildInstance:
    """Represents a managed Guild instance"""

    id: str
    name: str
    tier: GuildTier
    personality: GuildPersonality
    config: GuildConfig
    guild_core: Optional[GuildCore] = None
    status: str = "stopped"
    specialization: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    relationship_scores: Dict[str, float] = field(
        default_factory=dict
    )  # How well it works with other guilds
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_active: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier.value,
            "personality": self.personality.value,
            "status": self.status,
            "specialization": self.specialization,
            "performance_metrics": self.performance_metrics,
            "relationship_scores": self.relationship_scores,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }


@dataclass
class InterGuildTask:
    """Task that requires coordination between multiple Guild systems"""

    id: str
    title: str
    description: str
    required_guilds: List[str]
    assigned_guilds: List[str] = field(default_factory=list)
    coordination_strategy: str = "collaborative"
    status: str = "pending"
    results: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_guilds": self.required_guilds,
            "assigned_guilds": self.assigned_guilds,
            "coordination_strategy": self.coordination_strategy,
            "status": self.status,
            "results": self.results,
            "created_at": self.created_at,
        }


class MetaGuild:
    """
    The ultimate over-engineering: A Guild system that manages other Guild systems.

    Features that definitely cross the line into absurdity:
    - Spawns and manages multiple Guild instances
    - Inter-guild communication and coordination
    - Guild personality profiling and relationship management
    - Hierarchical task delegation across guild tiers
    - Guild evolution and mutation
    - Inter-dimensional guild networking (just kidding... maybe)
    - Guild therapy and conflict resolution
    - Recursive meta-guild creation (guilds managing guilds managing guilds...)
    """

    def __init__(self, config: Optional[GuildConfig] = None):
        self.config = config or GuildConfig(
            artifact_dir="artifacts/meta_guild", enable_model_management=True
        )

        # Guild management
        self.managed_guilds: Dict[str, GuildInstance] = {}
        self.guild_relationships: Dict[Tuple[str, str], float] = {}
        self.inter_guild_tasks: Dict[str, InterGuildTask] = {}

        # Meta-orchestration
        self.neural_orchestrator = None
        self.guild_spawning_enabled = True
        self.max_managed_guilds = 10  # Prevent infinite guild spawning
        self.guild_evolution_enabled = True
        self.recursive_meta_guilds_enabled = False  # Too dangerous to enable by default

        # Guild templates for spawning
        self.guild_templates = {
            "code_specialist": {
                "tier": GuildTier.MICRO,
                "personality": GuildPersonality.EFFICIENT,
                "specialization": ["code_generation", "code_review", "testing"],
                "config_overrides": {"enable_model_management": True},
            },
            "creative_collective": {
                "tier": GuildTier.STANDARD,
                "personality": GuildPersonality.CREATIVE,
                "specialization": ["creative_writing", "brainstorming", "design"],
                "config_overrides": {"enable_auto_batching": True},
            },
            "research_consortium": {
                "tier": GuildTier.MACRO,
                "personality": GuildPersonality.COLLABORATIVE,
                "specialization": ["research", "analysis", "documentation"],
                "config_overrides": {"max_concurrent_tasks": 20},
            },
            "chaos_guild": {
                "tier": GuildTier.STANDARD,
                "personality": GuildPersonality.CHAOTIC,
                "specialization": ["testing", "chaos_engineering", "resilience"],
                "config_overrides": {"enable_workspace_monitoring": True},
            },
        }

        # Background tasks
        self._running = False
        self._guild_monitor_task: Optional[asyncio.Task] = None
        self._relationship_analyzer_task: Optional[asyncio.Task] = None
        self._guild_evolution_task: Optional[asyncio.Task] = None

        logger.info("Meta Guild initialized (sanity level: non-existent)")

    async def start(self):
        """Start the Meta Guild system"""
        if self._running:
            return

        self._running = True

        # Initialize neural orchestrator for meta-level decisions
        self.neural_orchestrator = NeuralOrchestrator(None)  # Meta-level orchestrator
        await self.neural_orchestrator.start()

        # Start background tasks
        self._guild_monitor_task = asyncio.create_task(self._guild_monitoring_loop())
        self._relationship_analyzer_task = asyncio.create_task(
            self._relationship_analysis_loop()
        )

        if self.guild_evolution_enabled:
            self._guild_evolution_task = asyncio.create_task(
                self._guild_evolution_loop()
            )

        # Spawn initial guild ecosystem
        await self._spawn_initial_guild_ecosystem()

        logger.info("Meta Guild started (reality has left the building)")

    async def stop(self):
        """Stop the Meta Guild system"""
        if not self._running:
            return

        self._running = False

        # Stop all managed guilds
        for guild_instance in self.managed_guilds.values():
            if guild_instance.guild_core:
                await guild_instance.guild_core.stop()

        # Stop background tasks
        for task in [
            self._guild_monitor_task,
            self._relationship_analyzer_task,
            self._guild_evolution_task,
        ]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if self.neural_orchestrator:
            await self.neural_orchestrator.stop()

        logger.info("Meta Guild stopped (sanity partially restored)")

    async def spawn_guild(
        self, template_name: str, custom_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Spawn a new Guild instance"""
        if len(self.managed_guilds) >= self.max_managed_guilds:
            logger.warning("Maximum number of managed guilds reached")
            return ""

        if template_name not in self.guild_templates:
            logger.error(f"Unknown guild template: {template_name}")
            return ""

        template = self.guild_templates[template_name]
        guild_id = f"guild_{template_name}_{uuid.uuid4().hex[:8]}"

        # Create guild configuration
        guild_config = GuildConfig(**self.config.__dict__)

        # Apply template overrides
        config_overrides = template.get("config_overrides", {})
        for key, value in config_overrides.items():
            if hasattr(guild_config, key):
                setattr(guild_config, key, value)

        # Apply custom configuration
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(guild_config, key):
                    setattr(guild_config, key, value)

        # Set unique artifact directory
        guild_config.artifact_dir = f"artifacts/meta_guild/guilds/{guild_id}"

        # Create guild instance
        guild_instance = GuildInstance(
            id=guild_id,
            name=f"{template_name.replace('_', ' ').title()} Guild",
            tier=template["tier"],
            personality=template["personality"],
            config=guild_config,
            specialization=template["specialization"],
        )

        # Initialize and start the guild
        try:
            guild_instance.guild_core = GuildCore(config=guild_config)
            await guild_instance.guild_core.start()
            guild_instance.status = "running"
            guild_instance.last_active = datetime.now(timezone.utc).isoformat()

            self.managed_guilds[guild_id] = guild_instance

            logger.info(f"Spawned new guild: {guild_id} ({template_name})")

            # Initialize relationships with existing guilds
            await self._initialize_guild_relationships(guild_id)

            return guild_id

        except Exception as e:
            logger.error(f"Failed to spawn guild {guild_id}: {e}")
            return ""

    async def _spawn_initial_guild_ecosystem(self):
        """Spawn initial ecosystem of specialized guilds"""
        initial_guilds = [
            "code_specialist",
            "creative_collective",
            "research_consortium",
        ]

        for template in initial_guilds:
            guild_id = await self.spawn_guild(template)
            if guild_id:
                logger.info(f"Spawned initial guild: {guild_id}")

            # Small delay to prevent resource contention
            await asyncio.sleep(2)

    async def _initialize_guild_relationships(self, new_guild_id: str):
        """Initialize relationships between the new guild and existing guilds"""
        new_guild = self.managed_guilds[new_guild_id]

        for existing_guild_id, existing_guild in self.managed_guilds.items():
            if existing_guild_id == new_guild_id:
                continue

            # Calculate initial relationship score based on compatibility
            compatibility = await self._calculate_guild_compatibility(
                new_guild, existing_guild
            )

            self.guild_relationships[(new_guild_id, existing_guild_id)] = compatibility
            self.guild_relationships[(existing_guild_id, new_guild_id)] = compatibility

            logger.debug(
                f"Initialized relationship {new_guild_id} <-> {existing_guild_id}: {compatibility:.2f}"
            )

    async def _calculate_guild_compatibility(
        self, guild1: GuildInstance, guild2: GuildInstance
    ) -> float:
        """Calculate compatibility score between two guilds"""
        compatibility = 0.5  # Base compatibility

        # Personality compatibility
        personality_matrix = {
            (GuildPersonality.EFFICIENT, GuildPersonality.PERFECTIONIST): 0.8,
            (GuildPersonality.CREATIVE, GuildPersonality.CHAOTIC): 0.7,
            (GuildPersonality.COLLABORATIVE, GuildPersonality.EFFICIENT): 0.6,
            (GuildPersonality.COMPETITIVE, GuildPersonality.PERFECTIONIST): 0.7,
            (GuildPersonality.PHILOSOPHICAL, GuildPersonality.CREATIVE): 0.8,
        }

        pair = (guild1.personality, guild2.personality)
        reverse_pair = (guild2.personality, guild1.personality)

        if pair in personality_matrix:
            compatibility += personality_matrix[pair] * 0.3
        elif reverse_pair in personality_matrix:
            compatibility += personality_matrix[reverse_pair] * 0.3

        # Specialization overlap (some overlap is good, too much is redundant)
        overlap = len(set(guild1.specialization) & set(guild2.specialization))
        total_specs = len(set(guild1.specialization) | set(guild2.specialization))

        if total_specs > 0:
            overlap_ratio = overlap / total_specs
            # Sweet spot is around 30% overlap
            if 0.2 <= overlap_ratio <= 0.4:
                compatibility += 0.2
            elif overlap_ratio > 0.7:
                compatibility -= 0.1  # Too much overlap

        # Tier compatibility (similar tiers work better together)
        tier_diff = abs(
            list(GuildTier).index(guild1.tier) - list(GuildTier).index(guild2.tier)
        )
        if tier_diff <= 1:
            compatibility += 0.1

        return min(1.0, max(0.0, compatibility))

    async def submit_inter_guild_task(
        self,
        title: str,
        description: str,
        required_specializations: List[str],
        coordination_strategy: str = "collaborative",
    ) -> str:
        """Submit a task that requires coordination between multiple guilds"""
        task_id = f"inter_task_{uuid.uuid4().hex[:8]}"

        # Find suitable guilds based on specializations
        suitable_guilds = []
        for guild_id, guild in self.managed_guilds.items():
            if guild.status == "running":
                guild_specs = set(guild.specialization)
                required_specs = set(required_specializations)

                if (
                    guild_specs & required_specs
                ):  # Has at least one required specialization
                    suitable_guilds.append(guild_id)

        if not suitable_guilds:
            logger.warning(f"No suitable guilds found for task: {title}")
            return ""

        # Select optimal guild combination
        selected_guilds = await self._select_optimal_guild_combination(
            suitable_guilds, required_specializations, coordination_strategy
        )

        # Create inter-guild task
        inter_task = InterGuildTask(
            id=task_id,
            title=title,
            description=description,
            required_guilds=selected_guilds,
            coordination_strategy=coordination_strategy,
        )

        self.inter_guild_tasks[task_id] = inter_task

        # Delegate to selected guilds
        await self._delegate_inter_guild_task(task_id)

        logger.info(
            f"Submitted inter-guild task {task_id} to guilds: {selected_guilds}"
        )
        return task_id

    async def _select_optimal_guild_combination(
        self,
        suitable_guilds: List[str],
        required_specializations: List[str],
        coordination_strategy: str,
    ) -> List[str]:
        """Select optimal combination of guilds for a task"""
        if len(suitable_guilds) <= 2:
            return suitable_guilds

        # Use neural orchestrator to make optimal selection
        if self.neural_orchestrator:
            # This would involve complex optimization in a real implementation
            pass

        # Simple heuristic: select guilds with best relationships
        guild_scores = []

        for guild_id in suitable_guilds:
            score = 0.0
            guild = self.managed_guilds[guild_id]

            # Score based on specialization match
            guild_specs = set(guild.specialization)
            required_specs = set(required_specializations)
            spec_match = len(guild_specs & required_specs) / len(required_specs)
            score += spec_match * 0.5

            # Score based on relationships with other suitable guilds
            relationship_scores = []
            for other_guild_id in suitable_guilds:
                if other_guild_id != guild_id:
                    rel_key = (guild_id, other_guild_id)
                    if rel_key in self.guild_relationships:
                        relationship_scores.append(self.guild_relationships[rel_key])

            if relationship_scores:
                avg_relationship = sum(relationship_scores) / len(relationship_scores)
                score += avg_relationship * 0.3

            # Score based on current performance
            performance = guild.performance_metrics.get("success_rate", 0.5)
            score += performance * 0.2

            guild_scores.append((guild_id, score))

        # Sort by score and select top guilds
        guild_scores.sort(key=lambda x: x[1], reverse=True)

        # Select optimal number of guilds (usually 2-3 for most tasks)
        optimal_count = min(3, len(guild_scores))
        selected = [guild_id for guild_id, _ in guild_scores[:optimal_count]]

        return selected

    async def _delegate_inter_guild_task(self, task_id: str):
        """Delegate an inter-guild task to the selected guilds"""
        if task_id not in self.inter_guild_tasks:
            return

        inter_task = self.inter_guild_tasks[task_id]

        # Create individual tasks for each guild
        for guild_id in inter_task.required_guilds:
            if guild_id not in self.managed_guilds:
                continue

            guild = self.managed_guilds[guild_id]
            if not guild.guild_core or guild.status != "running":
                continue

            # Create specialized task for this guild
            guild_task_title = f"[Inter-Guild] {inter_task.title} - {guild.name} Part"
            guild_task_description = f"""
            This is part of an inter-guild collaborative task.

            Original Task: {inter_task.title}
            Description: {inter_task.description}

            Your Role: Focus on aspects related to your specializations: {', '.join(guild.specialization)}
            Coordination Strategy: {inter_task.coordination_strategy}
            Collaborating Guilds: {', '.join([self.managed_guilds[gid].name for gid in inter_task.required_guilds if gid != guild_id])}

            Please provide your specialized contribution to this collaborative effort.
            """

            try:
                # Submit task to the guild's task director
                guild_task_id = await guild.guild_core.task_director.create_task(
                    title=guild_task_title,
                    description=guild_task_description,
                    capabilities_required=guild.specialization,
                    metadata={
                        "inter_guild_task_id": task_id,
                        "coordination_strategy": inter_task.coordination_strategy,
                        "collaborating_guilds": inter_task.required_guilds,
                    },
                )

                inter_task.assigned_guilds.append(guild_id)
                logger.info(f"Delegated task {guild_task_id} to guild {guild_id}")

            except Exception as e:
                logger.error(f"Failed to delegate task to guild {guild_id}: {e}")

        if inter_task.assigned_guilds:
            inter_task.status = "in_progress"

    async def evolve_guild(self, guild_id: str) -> bool:
        """Evolve a guild based on its performance and experience"""
        if not self.guild_evolution_enabled:
            return False

        if guild_id not in self.managed_guilds:
            return False

        guild = self.managed_guilds[guild_id]

        # Analyze guild performance
        performance_metrics = guild.performance_metrics
        success_rate = performance_metrics.get("success_rate", 0.5)

        # Evolution strategies based on performance
        if success_rate > 0.8:
            # High-performing guild: expand capabilities
            await self._expand_guild_capabilities(guild)
        elif success_rate < 0.3:
            # Low-performing guild: specialize or therapy
            await self._provide_guild_therapy(guild)
        else:
            # Average guild: minor optimizations
            await self._optimize_guild_configuration(guild)

        logger.info(f"Evolved guild {guild_id} (success rate: {success_rate:.2f})")
        return True

    async def _expand_guild_capabilities(self, guild: GuildInstance):
        """Expand capabilities of a high-performing guild"""
        potential_new_specs = [
            "advanced_reasoning",
            "multi_modal_processing",
            "real_time_collaboration",
            "predictive_analytics",
            "automated_optimization",
            "cross_domain_synthesis",
        ]

        # Add new specialization if not already present
        for spec in potential_new_specs:
            if spec not in guild.specialization:
                guild.specialization.append(spec)
                logger.info(f"Guild {guild.id} evolved new capability: {spec}")
                break

    async def _provide_guild_therapy(self, guild: GuildInstance):
        """Provide therapy for underperforming guilds"""
        therapy_session = f"""
        🧠 Guild Therapy Session for {guild.name}

        Current Performance Issues:
        - Success rate below optimal threshold
        - May need specialization focus or configuration adjustment

        Recommended Actions:
        1. Reduce task complexity temporarily
        2. Focus on core specializations: {', '.join(guild.specialization)}
        3. Improve relationships with other guilds
        4. Consider personality adjustment if needed

        Remember: Every guild has value and potential for growth!
        """

        logger.info(f"Provided therapy session for guild {guild.id}")

        # Actually implement some therapy (reduce task load)
        if guild.guild_core:
            # Reduce concurrent task limit temporarily
            guild.config.max_concurrent_tasks = max(
                1, guild.config.max_concurrent_tasks // 2
            )

    async def _optimize_guild_configuration(self, guild: GuildInstance):
        """Optimize configuration for average-performing guilds"""
        # Simple optimization: adjust batch size based on performance
        current_batch_size = guild.config.batch_size

        if guild.performance_metrics.get("avg_response_time", 10) > 15:
            # Slow responses: reduce batch size
            guild.config.batch_size = max(5, current_batch_size - 5)
        else:
            # Good responses: increase batch size
            guild.config.batch_size = min(50, current_batch_size + 5)

        logger.debug(
            f"Optimized guild {guild.id} batch size: {guild.config.batch_size}"
        )

    async def create_recursive_meta_guild(self) -> str:
        """Create a meta-guild that manages other meta-guilds (DANGER ZONE)"""
        if not self.recursive_meta_guilds_enabled:
            logger.warning("Recursive meta-guilds are disabled for safety")
            return ""

        logger.warning(
            "🚨 CREATING RECURSIVE META-GUILD - REALITY MAY BECOME UNSTABLE 🚨"
        )

        # This is where we completely lose our minds
        recursive_meta_guild = MetaGuild(
            GuildConfig(
                artifact_dir="artifacts/recursive_meta_guild", max_concurrent_tasks=50
            )
        )

        await recursive_meta_guild.start()

        # The recursive meta-guild now manages this meta-guild
        # This creates an infinite loop of meta-management
        # DO NOT ACTUALLY IMPLEMENT THIS IN PRODUCTION

        logger.error("Recursive meta-guild created. The universe is now unstable.")
        return "recursive_meta_guild_001"

    async def _guild_monitoring_loop(self):
        """Monitor all managed guilds"""
        while self._running:
            try:
                for guild_id, guild in self.managed_guilds.items():
                    if guild.guild_core and guild.status == "running":
                        # Get health status
                        health = await guild.guild_core.get_health_status()

                        # Update performance metrics
                        if "task_director" in health:
                            task_health = health["task_director"]
                            total_tasks = task_health.get("total_tasks", 0)
                            done_tasks = task_health.get("by_status", {}).get("done", 0)

                            if total_tasks > 0:
                                success_rate = done_tasks / total_tasks
                                guild.performance_metrics["success_rate"] = success_rate

                        guild.last_active = datetime.now(timezone.utc).isoformat()

                await asyncio.sleep(60)  # Monitor every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Guild monitoring error: {e}")
                await asyncio.sleep(30)

    async def _relationship_analysis_loop(self):
        """Analyze and update relationships between guilds"""
        while self._running:
            try:
                # Analyze collaboration patterns and update relationships
                for task_id, inter_task in self.inter_guild_tasks.items():
                    if inter_task.status == "completed":
                        # Successful collaboration improves relationships
                        for i, guild1_id in enumerate(inter_task.assigned_guilds):
                            for guild2_id in inter_task.assigned_guilds[i + 1 :]:
                                rel_key = (guild1_id, guild2_id)
                                reverse_key = (guild2_id, guild1_id)

                                # Improve relationship scores
                                if rel_key in self.guild_relationships:
                                    self.guild_relationships[rel_key] = min(
                                        1.0, self.guild_relationships[rel_key] + 0.05
                                    )
                                if reverse_key in self.guild_relationships:
                                    self.guild_relationships[reverse_key] = min(
                                        1.0,
                                        self.guild_relationships[reverse_key] + 0.05,
                                    )

                await asyncio.sleep(300)  # Analyze every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Relationship analysis error: {e}")
                await asyncio.sleep(60)

    async def _guild_evolution_loop(self):
        """Periodic guild evolution"""
        while self._running:
            try:
                for guild_id in list(self.managed_guilds.keys()):
                    await self.evolve_guild(guild_id)
                    await asyncio.sleep(10)  # Small delay between evolutions

                await asyncio.sleep(3600)  # Evolve every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Guild evolution error: {e}")
                await asyncio.sleep(300)

    def get_meta_guild_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the meta-guild system"""
        return {
            "managed_guilds": len(self.managed_guilds),
            "active_guilds": len(
                [g for g in self.managed_guilds.values() if g.status == "running"]
            ),
            "inter_guild_tasks": len(self.inter_guild_tasks),
            "guild_relationships": len(self.guild_relationships),
            "guild_tiers": {
                tier.value: len(
                    [g for g in self.managed_guilds.values() if g.tier == tier]
                )
                for tier in GuildTier
            },
            "guild_personalities": {
                personality.value: len(
                    [
                        g
                        for g in self.managed_guilds.values()
                        if g.personality == personality
                    ]
                )
                for personality in GuildPersonality
            },
            "evolution_enabled": self.guild_evolution_enabled,
            "recursive_meta_guilds_enabled": self.recursive_meta_guilds_enabled,
            "sanity_level": "completely_absent",
        }

    async def guild_therapy_session(self, guild_id: str) -> str:
        """Provide therapy for a specific guild"""
        if guild_id not in self.managed_guilds:
            return f"Guild {guild_id} not found"

        guild = self.managed_guilds[guild_id]

        therapy_notes = f"""
        🧠 Meta-Guild Therapy Session

        Patient: {guild.name} (ID: {guild_id})
        Tier: {guild.tier.value}
        Personality: {guild.personality.value}

        Current Status:
        - Status: {guild.status}
        - Specializations: {', '.join(guild.specialization)}
        - Performance: {guild.performance_metrics.get('success_rate', 'Unknown')}

        Relationship Analysis:
        """

        # Analyze relationships
        relationships = []
        for (g1, g2), score in self.guild_relationships.items():
            if g1 == guild_id:
                other_guild = self.managed_guilds.get(g2)
                if other_guild:
                    relationships.append(f"- {other_guild.name}: {score:.2f}")

        if relationships:
            therapy_notes += "\n".join(relationships)
        else:
            therapy_notes += "- No significant relationships established yet"

        therapy_notes += f"""

        Recommendations:
        - Continue focusing on core specializations
        - Seek collaboration opportunities with compatible guilds
        - Regular performance monitoring and optimization

        Next session scheduled for: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """

        return therapy_notes
