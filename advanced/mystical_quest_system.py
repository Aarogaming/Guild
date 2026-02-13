"""
Mystical Quest System - Epic Adventures in Digital Realms

This system adds a quest-based approach to task management, where tasks
become epic adventures with rewards, challenges, and mystical progression.

Features:
- Epic quests with multiple stages and objectives
- Mystical rewards and artifact discovery
- Guild reputation and honor systems
- Legendary quest chains and saga completion
- Mystical creature encounters during quests
- Ancient prophecy fulfillment through quest completion
"""

import asyncio
import uuid
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from loguru import logger

from .mystical_guild import MagicalElement, SpellType, MagicalRank, MagicalAgent


class QuestDifficulty(Enum):
    """Quest difficulty levels"""

    TRIVIAL = "trivial"  # Simple tasks, minimal rewards
    EASY = "easy"  # Basic challenges
    MODERATE = "moderate"  # Standard difficulty
    HARD = "hard"  # Challenging quests
    EPIC = "epic"  # Major undertakings
    LEGENDARY = "legendary"  # Legendary achievements
    MYTHICAL = "mythical"  # Reality-bending quests


class QuestType(Enum):
    """Types of mystical quests"""

    EXPLORATION = "exploration"  # Discover new code territories
    COMBAT = "combat"  # Battle bugs and errors
    CRAFTING = "crafting"  # Create magical artifacts
    DIPLOMACY = "diplomacy"  # Negotiate with other systems
    MYSTERY = "mystery"  # Solve coding mysteries
    RESCUE = "rescue"  # Save corrupted data
    COLLECTION = "collection"  # Gather mystical resources
    BOSS_BATTLE = "boss_battle"  # Face legendary challenges


class QuestStatus(Enum):
    """Quest completion status"""

    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    LEGENDARY_COMPLETE = "legendary_complete"


@dataclass
class QuestObjective:
    """Individual quest objective"""

    id: str
    description: str
    objective_type: str  # "defeat", "collect", "create", "discover", etc.
    target: str
    required_amount: int = 1
    current_progress: int = 0
    completed: bool = False

    def update_progress(self, amount: int = 1) -> bool:
        """Update objective progress"""
        self.current_progress = min(
            self.required_amount, self.current_progress + amount
        )
        self.completed = self.current_progress >= self.required_amount
        return self.completed


@dataclass
class QuestReward:
    """Rewards for completing quests"""

    experience_points: int = 0
    guild_reputation: int = 0
    magical_artifacts: List[str] = field(default_factory=list)
    spell_scrolls: List[SpellType] = field(default_factory=list)
    mystical_currency: int = 0
    special_abilities: List[str] = field(default_factory=list)
    legendary_titles: List[str] = field(default_factory=list)


@dataclass
class MysticalQuest:
    """A mystical quest with objectives and rewards"""

    id: str
    title: str
    description: str
    quest_type: QuestType
    difficulty: QuestDifficulty
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: QuestReward = field(default_factory=QuestReward)

    # Quest properties
    status: QuestStatus = QuestStatus.AVAILABLE
    assigned_agent: Optional[str] = None
    required_rank: MagicalRank = MagicalRank.APPRENTICE
    required_elements: List[MagicalElement] = field(default_factory=list)

    # Quest progression
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    completion_percentage: float = 0.0

    # Mystical properties
    prophecy_related: bool = False
    artifact_discovery_chance: float = 0.1
    legendary_encounter_chance: float = 0.05
    divine_blessing_chance: float = 0.02

    def calculate_completion_percentage(self) -> float:
        """Calculate quest completion percentage"""
        if not self.objectives:
            return 0.0

        total_progress = sum(obj.current_progress for obj in self.objectives)
        total_required = sum(obj.required_amount for obj in self.objectives)

        if total_required == 0:
            return 100.0

        self.completion_percentage = (total_progress / total_required) * 100.0
        return self.completion_percentage

    def is_completed(self) -> bool:
        """Check if quest is completed"""
        return all(obj.completed for obj in self.objectives)

    def can_be_assigned_to(self, agent: MagicalAgent) -> bool:
        """Check if quest can be assigned to agent"""
        # Check rank requirement
        if agent.magical_rank.value < self.required_rank.value:
            return False

        # Check elemental requirements
        if self.required_elements:
            agent_elements = [agent.primary_element]
            if agent.secondary_element:
                agent_elements.append(agent.secondary_element)

            if not any(element in agent_elements for element in self.required_elements):
                return False

        return True


class MysticalQuestSystem:
    """
    The Mystical Quest System transforms mundane tasks into epic adventures.

    Features:
    - Dynamic quest generation based on system needs
    - Progressive difficulty scaling with agent advancement
    - Mystical rewards including artifacts and special abilities
    - Legendary quest chains that span multiple adventures
    - Random encounters with mystical creatures
    - Prophecy fulfillment through quest completion
    - Guild reputation and honor systems
    """

    def __init__(self, mystical_guild=None):
        self.mystical_guild = mystical_guild
        self._running = False

        # Quest management
        self.available_quests: Dict[str, MysticalQuest] = {}
        self.active_quests: Dict[str, MysticalQuest] = {}
        self.completed_quests: Dict[str, MysticalQuest] = {}

        # Quest generation
        self.quest_templates: Dict[QuestType, List[Dict[str, Any]]] = {}
        self.legendary_quest_chains: Dict[str, List[str]] = {}

        # Reputation and progression
        self.agent_reputations: Dict[str, int] = {}
        self.guild_honor: int = 0
        self.legendary_achievements: List[str] = []

        # Mystical encounters
        self.creature_encounters: Dict[str, Dict[str, Any]] = {}
        self.artifact_discoveries: List[Dict[str, Any]] = []

        # Background processes
        self.quest_generation_task: Optional[asyncio.Task] = None
        self.encounter_management_task: Optional[asyncio.Task] = None

        # Initialize quest system
        self._initialize_quest_templates()
        self._initialize_legendary_chains()

        logger.info("⚔️ Mystical Quest System initialized - Adventures await!")

    def _initialize_quest_templates(self):
        """Initialize quest templates for dynamic generation"""

        self.quest_templates = {
            QuestType.EXPLORATION: [
                {
                    "title": "Explore the Forgotten Code Caverns",
                    "description": "Venture into the depths of legacy code to discover hidden algorithms",
                    "objectives": [
                        {
                            "type": "discover",
                            "target": "ancient_algorithm",
                            "amount": 3,
                        },
                        {"type": "map", "target": "code_structure", "amount": 1},
                    ],
                },
                {
                    "title": "Chart the Mystical API Territories",
                    "description": "Map the uncharted regions of external API integrations",
                    "objectives": [
                        {"type": "discover", "target": "api_endpoint", "amount": 5},
                        {"type": "test", "target": "api_connection", "amount": 3},
                    ],
                },
            ],
            QuestType.COMBAT: [
                {
                    "title": "Slay the Memory Leak Dragon",
                    "description": "Hunt down and eliminate the fearsome memory leak that terrorizes the system",
                    "objectives": [
                        {"type": "identify", "target": "memory_leak", "amount": 1},
                        {"type": "defeat", "target": "memory_leak", "amount": 1},
                        {"type": "verify", "target": "memory_stability", "amount": 1},
                    ],
                },
                {
                    "title": "Battle the Null Pointer Demons",
                    "description": "Engage in combat with the dreaded null pointer exceptions",
                    "objectives": [
                        {"type": "detect", "target": "null_pointer", "amount": 5},
                        {"type": "defeat", "target": "null_pointer", "amount": 5},
                        {"type": "fortify", "target": "null_safety", "amount": 1},
                    ],
                },
            ],
            QuestType.CRAFTING: [
                {
                    "title": "Forge the Legendary Optimization Artifact",
                    "description": "Craft a powerful artifact that enhances system performance",
                    "objectives": [
                        {
                            "type": "gather",
                            "target": "performance_metrics",
                            "amount": 10,
                        },
                        {"type": "analyze", "target": "bottlenecks", "amount": 3},
                        {
                            "type": "create",
                            "target": "optimization_artifact",
                            "amount": 1,
                        },
                    ],
                },
                {
                    "title": "Brew the Potion of Perfect Testing",
                    "description": "Create a mystical potion that ensures comprehensive test coverage",
                    "objectives": [
                        {"type": "collect", "target": "test_cases", "amount": 20},
                        {"type": "refine", "target": "test_quality", "amount": 5},
                        {"type": "brew", "target": "testing_potion", "amount": 1},
                    ],
                },
            ],
            QuestType.MYSTERY: [
                {
                    "title": "Solve the Mystery of the Vanishing Variables",
                    "description": "Investigate the strange case of variables that disappear without a trace",
                    "objectives": [
                        {
                            "type": "investigate",
                            "target": "variable_scope",
                            "amount": 3,
                        },
                        {"type": "analyze", "target": "memory_patterns", "amount": 2},
                        {"type": "solve", "target": "mystery", "amount": 1},
                    ],
                }
            ],
            QuestType.BOSS_BATTLE: [
                {
                    "title": "Confront the Ancient Monolith of Technical Debt",
                    "description": "Face the ultimate challenge: refactoring the legendary monolith",
                    "objectives": [
                        {
                            "type": "analyze",
                            "target": "monolith_structure",
                            "amount": 1,
                        },
                        {"type": "plan", "target": "refactoring_strategy", "amount": 1},
                        {
                            "type": "execute",
                            "target": "monolith_refactoring",
                            "amount": 1,
                        },
                        {"type": "verify", "target": "system_stability", "amount": 1},
                    ],
                }
            ],
        }

    def _initialize_legendary_chains(self):
        """Initialize legendary quest chains"""

        self.legendary_quest_chains = {
            "The Saga of Perfect Code": [
                "achieve_zero_bugs",
                "master_all_design_patterns",
                "create_self_documenting_code",
                "transcend_technical_debt",
            ],
            "The Chronicles of System Mastery": [
                "optimize_all_algorithms",
                "achieve_perfect_scalability",
                "master_distributed_computing",
                "become_architecture_legend",
            ],
            "The Legend of the Digital Sage": [
                "mentor_junior_developers",
                "create_revolutionary_framework",
                "solve_impossible_problem",
                "achieve_coding_enlightenment",
            ],
        }

    async def start(self):
        """Start the mystical quest system"""
        if self._running:
            return

        self._running = True

        # Generate initial quests
        await self._generate_initial_quests()

        # Start background processes
        self.quest_generation_task = asyncio.create_task(self._quest_generation_loop())
        self.encounter_management_task = asyncio.create_task(
            self._encounter_management_loop()
        )

        logger.info("⚔️ Mystical Quest System started - Epic adventures begin!")

    async def stop(self):
        """Stop the mystical quest system"""
        if not self._running:
            return

        self._running = False

        # Stop background processes
        for task in [self.quest_generation_task, self.encounter_management_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("⚔️ Mystical Quest System stopped - Adventures conclude")

    async def _generate_initial_quests(self):
        """Generate initial set of quests"""

        # Generate quests of various types and difficulties
        quest_configs = [
            (QuestType.EXPLORATION, QuestDifficulty.EASY),
            (QuestType.COMBAT, QuestDifficulty.MODERATE),
            (QuestType.CRAFTING, QuestDifficulty.MODERATE),
            (QuestType.MYSTERY, QuestDifficulty.HARD),
            (QuestType.BOSS_BATTLE, QuestDifficulty.EPIC),
        ]

        for quest_type, difficulty in quest_configs:
            quest_id = await self.generate_quest(quest_type, difficulty)
            logger.info(f"⚔️ Generated initial quest: {quest_id}")

    async def generate_quest(
        self, quest_type: QuestType, difficulty: QuestDifficulty
    ) -> str:
        """Generate a new mystical quest"""

        quest_id = f"quest_{uuid.uuid4().hex[:8]}"

        # Select template
        templates = self.quest_templates.get(quest_type, [])
        if not templates:
            logger.warning(f"No templates available for quest type: {quest_type}")
            return quest_id

        template = random.choice(templates)

        # Create quest objectives
        objectives = []
        for i, obj_template in enumerate(template["objectives"]):
            objective = QuestObjective(
                id=f"{quest_id}_obj_{i}",
                description=f"{obj_template['type'].title()} {obj_template['target']}",
                objective_type=obj_template["type"],
                target=obj_template["target"],
                required_amount=obj_template["amount"],
            )
            objectives.append(objective)

        # Generate rewards based on difficulty
        rewards = self._generate_quest_rewards(difficulty)

        # Create the quest
        quest = MysticalQuest(
            id=quest_id,
            title=template["title"],
            description=template["description"],
            quest_type=quest_type,
            difficulty=difficulty,
            objectives=objectives,
            rewards=rewards,
            required_rank=self._get_required_rank_for_difficulty(difficulty),
            artifact_discovery_chance=self._get_discovery_chance(difficulty),
            legendary_encounter_chance=self._get_encounter_chance(difficulty),
        )

        self.available_quests[quest_id] = quest

        logger.info(
            f"⚔️ Generated {difficulty.value} {quest_type.value} quest: {quest.title}"
        )
        return quest_id

    def _generate_quest_rewards(self, difficulty: QuestDifficulty) -> QuestReward:
        """Generate rewards based on quest difficulty"""

        base_rewards = {
            QuestDifficulty.TRIVIAL: {"xp": 10, "rep": 1, "currency": 5},
            QuestDifficulty.EASY: {"xp": 25, "rep": 3, "currency": 15},
            QuestDifficulty.MODERATE: {"xp": 50, "rep": 5, "currency": 30},
            QuestDifficulty.HARD: {"xp": 100, "rep": 10, "currency": 60},
            QuestDifficulty.EPIC: {"xp": 200, "rep": 20, "currency": 120},
            QuestDifficulty.LEGENDARY: {"xp": 500, "rep": 50, "currency": 300},
            QuestDifficulty.MYTHICAL: {"xp": 1000, "rep": 100, "currency": 600},
        }

        base = base_rewards.get(difficulty, base_rewards[QuestDifficulty.MODERATE])

        rewards = QuestReward(
            experience_points=base["xp"],
            guild_reputation=base["rep"],
            mystical_currency=base["currency"],
        )

        # Add special rewards for higher difficulties
        if difficulty.value >= QuestDifficulty.HARD.value:
            rewards.magical_artifacts.append(f"artifact_of_{difficulty.value}")

        if difficulty.value >= QuestDifficulty.EPIC.value:
            rewards.spell_scrolls.append(random.choice(list(SpellType)))

        if difficulty.value >= QuestDifficulty.LEGENDARY.value:
            rewards.legendary_titles.append(f"Legend of {difficulty.value.title()}")

        return rewards

    def _get_required_rank_for_difficulty(
        self, difficulty: QuestDifficulty
    ) -> MagicalRank:
        """Get required magical rank for difficulty"""

        rank_mapping = {
            QuestDifficulty.TRIVIAL: MagicalRank.APPRENTICE,
            QuestDifficulty.EASY: MagicalRank.APPRENTICE,
            QuestDifficulty.MODERATE: MagicalRank.ADEPT,
            QuestDifficulty.HARD: MagicalRank.MAGE,
            QuestDifficulty.EPIC: MagicalRank.WIZARD,
            QuestDifficulty.LEGENDARY: MagicalRank.ARCHMAGE,
            QuestDifficulty.MYTHICAL: MagicalRank.DIGITAL_DEITY,
        }

        return rank_mapping.get(difficulty, MagicalRank.APPRENTICE)

    def _get_discovery_chance(self, difficulty: QuestDifficulty) -> float:
        """Get artifact discovery chance for difficulty"""

        chances = {
            QuestDifficulty.TRIVIAL: 0.05,
            QuestDifficulty.EASY: 0.1,
            QuestDifficulty.MODERATE: 0.15,
            QuestDifficulty.HARD: 0.25,
            QuestDifficulty.EPIC: 0.4,
            QuestDifficulty.LEGENDARY: 0.6,
            QuestDifficulty.MYTHICAL: 0.8,
        }

        return chances.get(difficulty, 0.1)

    def _get_encounter_chance(self, difficulty: QuestDifficulty) -> float:
        """Get legendary encounter chance for difficulty"""

        chances = {
            QuestDifficulty.TRIVIAL: 0.01,
            QuestDifficulty.EASY: 0.02,
            QuestDifficulty.MODERATE: 0.05,
            QuestDifficulty.HARD: 0.1,
            QuestDifficulty.EPIC: 0.2,
            QuestDifficulty.LEGENDARY: 0.35,
            QuestDifficulty.MYTHICAL: 0.5,
        }

        return chances.get(difficulty, 0.05)

    async def assign_quest(self, quest_id: str, agent_id: str) -> bool:
        """Assign a quest to a magical agent"""

        if quest_id not in self.available_quests:
            logger.warning(f"Quest {quest_id} not available")
            return False

        if (
            not self.mystical_guild
            or agent_id not in self.mystical_guild.magical_agents
        ):
            logger.warning(f"Agent {agent_id} not found")
            return False

        quest = self.available_quests[quest_id]
        agent = self.mystical_guild.magical_agents[agent_id]

        # Check if agent can take the quest
        if not quest.can_be_assigned_to(agent):
            logger.warning(f"Agent {agent.name} cannot take quest {quest.title}")
            return False

        # Assign the quest
        quest.assigned_agent = agent_id
        quest.status = QuestStatus.IN_PROGRESS
        quest.started_at = datetime.now(timezone.utc).isoformat()

        # Move to active quests
        self.active_quests[quest_id] = quest
        del self.available_quests[quest_id]

        logger.info(f"⚔️ Quest '{quest.title}' assigned to {agent.name}")
        return True

    async def update_quest_progress(
        self, quest_id: str, objective_type: str, target: str, amount: int = 1
    ) -> bool:
        """Update progress on a quest objective"""

        if quest_id not in self.active_quests:
            return False

        quest = self.active_quests[quest_id]

        # Find matching objective
        for objective in quest.objectives:
            if (
                objective.objective_type == objective_type
                and objective.target == target
            ):
                objective.update_progress(amount)

                logger.info(
                    f"⚔️ Quest progress: {objective.description} "
                    f"({objective.current_progress}/{objective.required_amount})"
                )

                # Check if quest is completed
                if quest.is_completed():
                    await self._complete_quest(quest_id)

                return True

        return False

    async def _complete_quest(self, quest_id: str):
        """Complete a quest and award rewards"""

        if quest_id not in self.active_quests:
            return

        quest = self.active_quests[quest_id]
        quest.status = QuestStatus.COMPLETED
        quest.completed_at = datetime.now(timezone.utc).isoformat()
        quest.completion_percentage = 100.0

        # Award rewards
        if quest.assigned_agent:
            await self._award_quest_rewards(quest.assigned_agent, quest.rewards)

        # Check for special events
        await self._check_for_special_quest_events(quest)

        # Move to completed quests
        self.completed_quests[quest_id] = quest
        del self.active_quests[quest_id]

        logger.info(f"🏆 Quest completed: {quest.title}")

        # Check for legendary chain progression
        await self._check_legendary_chain_progression(quest)

    async def _award_quest_rewards(self, agent_id: str, rewards: QuestReward):
        """Award quest rewards to an agent"""

        if (
            not self.mystical_guild
            or agent_id not in self.mystical_guild.magical_agents
        ):
            return

        agent = self.mystical_guild.magical_agents[agent_id]

        # Award experience points
        agent.experience_points += rewards.experience_points

        # Award reputation
        current_rep = self.agent_reputations.get(agent_id, 0)
        self.agent_reputations[agent_id] = current_rep + rewards.guild_reputation

        # Award guild honor
        self.guild_honor += rewards.guild_reputation

        # Award magical artifacts
        for artifact_id in rewards.magical_artifacts:
            if artifact_id not in agent.magical_artifacts:
                agent.magical_artifacts.append(artifact_id)

        # Learn new spells
        for spell in rewards.spell_scrolls:
            if spell not in agent.spell_repertoire:
                agent.spell_repertoire.append(spell)

        # Award legendary titles
        for title in rewards.legendary_titles:
            if title not in self.legendary_achievements:
                self.legendary_achievements.append(title)

        logger.info(
            f"🏆 Rewards awarded to {agent.name}: "
            f"{rewards.experience_points} XP, {rewards.guild_reputation} reputation"
        )

    async def _check_for_special_quest_events(self, quest: MysticalQuest):
        """Check for special events during quest completion"""

        # Artifact discovery
        if random.random() < quest.artifact_discovery_chance:
            await self._discover_mystical_artifact(quest)

        # Legendary encounter
        if random.random() < quest.legendary_encounter_chance:
            await self._trigger_legendary_encounter(quest)

        # Divine blessing
        if random.random() < quest.divine_blessing_chance:
            await self._receive_divine_blessing(quest)

    async def _discover_mystical_artifact(self, quest: MysticalQuest):
        """Discover a mystical artifact during quest"""

        artifact_types = ["Crystal", "Scroll", "Amulet", "Staff", "Orb"]
        artifact_powers = ["Speed", "Wisdom", "Power", "Protection", "Insight"]

        artifact_name = (
            f"{random.choice(artifact_powers)} {random.choice(artifact_types)}"
        )

        discovery = {
            "artifact_name": artifact_name,
            "quest_id": quest.id,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "power_level": random.uniform(0.5, 1.0),
        }

        self.artifact_discoveries.append(discovery)

        logger.info(f"✨ Mystical artifact discovered: {artifact_name}")

    async def _trigger_legendary_encounter(self, quest: MysticalQuest):
        """Trigger a legendary creature encounter"""

        creatures = [
            "Ancient Code Dragon",
            "Legendary Bug Sphinx",
            "Mystical Algorithm Phoenix",
            "Divine Performance Unicorn",
            "Sacred Memory Guardian",
        ]

        creature_name = random.choice(creatures)

        encounter = {
            "creature_name": creature_name,
            "quest_id": quest.id,
            "encountered_at": datetime.now(timezone.utc).isoformat(),
            "outcome": random.choice(["friendly", "challenging", "wise", "mysterious"]),
        }

        self.creature_encounters[f"encounter_{uuid.uuid4().hex[:8]}"] = encounter

        logger.info(f"🐉 Legendary encounter: {creature_name}")

    async def _receive_divine_blessing(self, quest: MysticalQuest):
        """Receive divine blessing for quest completion"""

        blessings = [
            "Blessing of Perfect Code",
            "Divine Optimization Grace",
            "Sacred Bug Immunity",
            "Celestial Performance Boost",
            "Holy Refactoring Power",
        ]

        blessing = random.choice(blessings)

        logger.info(f"🙏 Divine blessing received: {blessing}")

    async def _check_legendary_chain_progression(self, quest: MysticalQuest):
        """Check if quest contributes to legendary chain progression"""

        # This would check if the completed quest is part of a legendary chain
        # and update progression accordingly

        for chain_name, chain_quests in self.legendary_quest_chains.items():
            if quest.id in chain_quests:
                logger.info(f"🌟 Legendary chain progress: {chain_name}")
                break

    async def _quest_generation_loop(self):
        """Continuously generate new quests"""
        while self._running:
            try:
                # Generate new quests if needed
                if (
                    len(self.available_quests) < 5
                ):  # Maintain at least 5 available quests
                    quest_type = random.choice(list(QuestType))
                    difficulty = random.choice(list(QuestDifficulty))
                    await self.generate_quest(quest_type, difficulty)

                await asyncio.sleep(300)  # Generate every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Quest generation loop error: {e}")
                await asyncio.sleep(120)

    async def _encounter_management_loop(self):
        """Manage random encounters and events"""
        while self._running:
            try:
                # Random mystical events
                if random.random() < 0.1:  # 10% chance per cycle
                    await self._trigger_random_mystical_event()

                await asyncio.sleep(180)  # Check every 3 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Encounter management loop error: {e}")
                await asyncio.sleep(90)

    async def _trigger_random_mystical_event(self):
        """Trigger random mystical events"""

        events = [
            "A shooting star grants bonus experience to all active quests",
            "The mystical winds carry whispers of hidden treasures",
            "Ancient spirits offer guidance to struggling adventurers",
            "A magical aurora enhances spell-casting abilities",
            "The digital realm shimmers with enhanced magical energy",
        ]

        event = random.choice(events)
        logger.info(f"🌟 Mystical event: {event}")

    def get_quest_system_status(self) -> Dict[str, Any]:
        """Get comprehensive quest system status"""

        return {
            "available_quests": len(self.available_quests),
            "active_quests": len(self.active_quests),
            "completed_quests": len(self.completed_quests),
            "guild_honor": self.guild_honor,
            "legendary_achievements": len(self.legendary_achievements),
            "artifact_discoveries": len(self.artifact_discoveries),
            "creature_encounters": len(self.creature_encounters),
            "agent_reputations": dict(self.agent_reputations),
            "legendary_chains": len(self.legendary_quest_chains),
            "system_status": "adventuring" if self._running else "resting",
        }

    async def demonstrate_quest_system(self) -> str:
        """Demonstrate the mystical quest system"""

        demo_results = []

        # Generate sample quests
        for quest_type in [QuestType.EXPLORATION, QuestType.COMBAT, QuestType.CRAFTING]:
            quest_id = await self.generate_quest(quest_type, QuestDifficulty.MODERATE)
            quest = self.available_quests[quest_id]
            demo_results.append(f"Generated quest: {quest.title}")

        # Show system status
        status = self.get_quest_system_status()
        demo_results.extend(
            [
                f"Available quests: {status['available_quests']}",
                f"Guild honor: {status['guild_honor']}",
                f"Legendary achievements: {status['legendary_achievements']}",
            ]
        )

        return "\n".join(
            [
                "⚔️🌟 MYSTICAL QUEST SYSTEM - EPIC ADVENTURES AWAIT",
                "=" * 60,
                "",
                *demo_results,
                "",
                "🏰 Transform mundane tasks into epic adventures!",
                "⚔️ Battle bugs, explore code realms, craft artifacts!",
                "🏆 Earn reputation, discover treasures, achieve legend status!",
                "🐉 Encounter mystical creatures and receive divine blessings!",
                "",
                "✨ Every task becomes a heroic quest in the digital realm!",
            ]
        )


if __name__ == "__main__":

    async def demo_quest_system():
        quest_system = MysticalQuestSystem()
        await quest_system.start()

        demonstration = await quest_system.demonstrate_quest_system()
        print(demonstration)

        await quest_system.stop()

    logger.info("⚔️ MYSTICAL QUEST SYSTEM DEMONSTRATION")
    asyncio.run(demo_quest_system())
