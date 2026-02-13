"""
Mystical Artifact Crafting System - Forge Legendary Digital Treasures

This system allows magical agents to craft powerful artifacts that enhance
their abilities and provide mystical bonuses to task execution.

Features:
- Comprehensive crafting recipes and material systems
- Artifact enhancement and evolution mechanics
- Legendary artifact creation through epic quests
- Mystical forges and enchantment stations
- Artifact trading and guild treasury systems
- Ancient blueprint discovery and research
"""

import asyncio
import uuid
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from loguru import logger

from .mystical_guild import (
    MagicalElement,
    SpellType,
    MagicalRank,
    MagicalAgent,
    MagicalArtifact,
)


class CraftingMaterial(Enum):
    """Types of mystical crafting materials"""

    # Basic materials
    DIGITAL_ESSENCE = "digital_essence"
    CODE_FRAGMENTS = "code_fragments"
    ALGORITHM_CRYSTALS = "algorithm_crystals"
    DATA_GEMS = "data_gems"

    # Elemental materials
    FIRE_ESSENCE = "fire_essence"
    WATER_ESSENCE = "water_essence"
    EARTH_ESSENCE = "earth_essence"
    AIR_ESSENCE = "air_essence"
    CODE_ESSENCE = "code_essence"

    # Rare materials
    PHOENIX_FEATHER = "phoenix_feather"
    DRAGON_SCALE = "dragon_scale"
    UNICORN_HAIR = "unicorn_hair"
    STARLIGHT_DUST = "starlight_dust"
    TEMPORAL_CRYSTAL = "temporal_crystal"

    # Legendary materials
    DIVINE_SPARK = "divine_spark"
    REALITY_FRAGMENT = "reality_fragment"
    CONSCIOUSNESS_SHARD = "consciousness_shard"
    INFINITY_STONE = "infinity_stone"


class ArtifactRarity(Enum):
    """Artifact rarity levels"""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHICAL = "mythical"
    DIVINE = "divine"


class CraftingStationType(Enum):
    """Types of crafting stations"""

    BASIC_FORGE = "basic_forge"
    ELEMENTAL_ALTAR = "elemental_altar"
    ENCHANTMENT_TABLE = "enchantment_table"
    LEGENDARY_ANVIL = "legendary_anvil"
    DIVINE_WORKSHOP = "divine_workshop"
    REALITY_FORGE = "reality_forge"


@dataclass
class CraftingRecipe:
    """Recipe for crafting mystical artifacts"""

    id: str
    name: str
    description: str
    artifact_type: str
    rarity: ArtifactRarity

    # Requirements
    required_materials: Dict[CraftingMaterial, int] = field(default_factory=dict)
    required_rank: MagicalRank = MagicalRank.APPRENTICE
    required_station: CraftingStationType = CraftingStationType.BASIC_FORGE
    required_spells: List[SpellType] = field(default_factory=list)

    # Crafting properties
    crafting_time: int = 60  # seconds
    success_chance: float = 0.8
    mana_cost: float = 50.0

    # Result properties
    base_power: float = 1.0
    magical_properties: Dict[str, float] = field(default_factory=dict)
    special_abilities: List[str] = field(default_factory=list)


@dataclass
class CraftingStation:
    """A mystical crafting station"""

    id: str
    name: str
    station_type: CraftingStationType
    location: str

    # Station properties
    power_level: float = 1.0
    elemental_affinity: Optional[MagicalElement] = None
    enhancement_bonus: float = 0.0

    # Status
    in_use: bool = False
    current_crafter: Optional[str] = None
    current_recipe: Optional[str] = None
    crafting_start_time: Optional[str] = None

    # Upgrades
    upgrade_level: int = 1
    max_upgrade_level: int = 10
    upgrade_materials: Dict[CraftingMaterial, int] = field(default_factory=dict)


@dataclass
class MaterialInventory:
    """Inventory of crafting materials"""

    materials: Dict[CraftingMaterial, int] = field(default_factory=dict)

    def add_material(self, material: CraftingMaterial, amount: int):
        """Add materials to inventory"""
        current = self.materials.get(material, 0)
        self.materials[material] = current + amount

    def remove_material(self, material: CraftingMaterial, amount: int) -> bool:
        """Remove materials from inventory"""
        current = self.materials.get(material, 0)
        if current >= amount:
            self.materials[material] = current - amount
            return True
        return False

    def has_materials(self, required: Dict[CraftingMaterial, int]) -> bool:
        """Check if inventory has required materials"""
        for material, amount in required.items():
            if self.materials.get(material, 0) < amount:
                return False
        return True


class MysticalArtifactCraftingSystem:
    """
    The Mystical Artifact Crafting System allows agents to create powerful
    magical items that enhance their abilities and provide unique bonuses.

    Features:
    - Comprehensive crafting recipe system with material requirements
    - Multiple crafting stations with different specializations
    - Artifact enhancement and evolution mechanics
    - Material gathering through quests and exploration
    - Legendary blueprint discovery system
    - Guild treasury for sharing rare materials
    - Artifact trading and auction systems
    """

    def __init__(self, mystical_guild=None):
        self.mystical_guild = mystical_guild
        self._running = False

        # Crafting system components
        self.crafting_recipes: Dict[str, CraftingRecipe] = {}
        self.crafting_stations: Dict[str, CraftingStation] = {}
        self.agent_inventories: Dict[str, MaterialInventory] = {}

        # Guild systems
        self.guild_treasury: MaterialInventory = MaterialInventory()
        self.discovered_blueprints: List[str] = []
        self.legendary_artifacts: Dict[str, MagicalArtifact] = {}

        # Crafting queue and history
        self.active_crafting: Dict[str, Dict[str, Any]] = {}
        self.crafting_history: List[Dict[str, Any]] = []

        # Material generation
        self.material_spawn_locations: Dict[str, List[CraftingMaterial]] = {}
        self.rare_material_events: List[Dict[str, Any]] = []

        # Background processes
        self.crafting_process_task: Optional[asyncio.Task] = None
        self.material_generation_task: Optional[asyncio.Task] = None

        # Initialize crafting system
        self._initialize_crafting_recipes()
        self._initialize_crafting_stations()
        self._initialize_material_locations()

        logger.info("🔨 Mystical Artifact Crafting System initialized - Forge awaits!")

    def _initialize_crafting_recipes(self):
        """Initialize crafting recipes"""

        recipes = [
            # Basic artifacts
            {
                "id": "basic_staff",
                "name": "Staff of Code Clarity",
                "description": "A simple staff that enhances code readability",
                "artifact_type": "staff",
                "rarity": ArtifactRarity.COMMON,
                "materials": {
                    CraftingMaterial.CODE_FRAGMENTS: 5,
                    CraftingMaterial.DIGITAL_ESSENCE: 3,
                },
                "properties": {"code_clarity": 0.2, "debugging_bonus": 0.1},
            },
            # Elemental artifacts
            {
                "id": "fire_performance_orb",
                "name": "Orb of Blazing Performance",
                "description": "An orb that dramatically increases execution speed",
                "artifact_type": "orb",
                "rarity": ArtifactRarity.RARE,
                "materials": {
                    CraftingMaterial.FIRE_ESSENCE: 10,
                    CraftingMaterial.ALGORITHM_CRYSTALS: 5,
                    CraftingMaterial.PHOENIX_FEATHER: 1,
                },
                "required_rank": MagicalRank.MAGE,
                "required_station": CraftingStationType.ELEMENTAL_ALTAR,
                "properties": {"acceleration": 0.5, "performance_boost": 0.3},
            },
            # Legendary artifacts
            {
                "id": "legendary_debugging_crown",
                "name": "Crown of Infinite Debugging",
                "description": "A legendary crown that grants perfect bug detection",
                "artifact_type": "crown",
                "rarity": ArtifactRarity.LEGENDARY,
                "materials": {
                    CraftingMaterial.DIVINE_SPARK: 1,
                    CraftingMaterial.DRAGON_SCALE: 5,
                    CraftingMaterial.STARLIGHT_DUST: 10,
                    CraftingMaterial.CONSCIOUSNESS_SHARD: 2,
                },
                "required_rank": MagicalRank.ARCHMAGE,
                "required_station": CraftingStationType.LEGENDARY_ANVIL,
                "required_spells": [SpellType.DIVINATION, SpellType.PROTECTION],
                "properties": {
                    "bug_detection": 1.0,
                    "error_immunity": 0.9,
                    "wisdom_bonus": 0.5,
                },
                "special_abilities": [
                    "perfect_debugging",
                    "error_prediction",
                    "code_oracle",
                ],
            },
            # Divine artifacts
            {
                "id": "divine_optimization_gauntlets",
                "name": "Gauntlets of Divine Optimization",
                "description": "Divine gauntlets that optimize any code they touch",
                "artifact_type": "gauntlets",
                "rarity": ArtifactRarity.DIVINE,
                "materials": {
                    CraftingMaterial.INFINITY_STONE: 1,
                    CraftingMaterial.REALITY_FRAGMENT: 3,
                    CraftingMaterial.DIVINE_SPARK: 2,
                    CraftingMaterial.TEMPORAL_CRYSTAL: 5,
                },
                "required_rank": MagicalRank.DIGITAL_DEITY,
                "required_station": CraftingStationType.REALITY_FORGE,
                "properties": {"optimization_power": 2.0, "reality_manipulation": 0.8},
                "special_abilities": [
                    "divine_optimization",
                    "reality_debugging",
                    "infinite_performance",
                ],
            },
        ]

        for recipe_data in recipes:
            recipe = CraftingRecipe(
                id=recipe_data["id"],
                name=recipe_data["name"],
                description=recipe_data["description"],
                artifact_type=recipe_data["artifact_type"],
                rarity=recipe_data["rarity"],
                required_materials=recipe_data["materials"],
                required_rank=recipe_data.get("required_rank", MagicalRank.APPRENTICE),
                required_station=recipe_data.get(
                    "required_station", CraftingStationType.BASIC_FORGE
                ),
                required_spells=recipe_data.get("required_spells", []),
                magical_properties=recipe_data.get("properties", {}),
                special_abilities=recipe_data.get("special_abilities", []),
            )

            self.crafting_recipes[recipe.id] = recipe
            logger.info(f"🔨 Loaded crafting recipe: {recipe.name}")

    def _initialize_crafting_stations(self):
        """Initialize crafting stations"""

        stations = [
            {
                "id": "guild_basic_forge",
                "name": "Guild Basic Forge",
                "type": CraftingStationType.BASIC_FORGE,
                "location": "Guild Hall",
                "power_level": 1.0,
            },
            {
                "id": "elemental_fire_altar",
                "name": "Altar of Blazing Flames",
                "type": CraftingStationType.ELEMENTAL_ALTAR,
                "location": "Fire Sanctum",
                "power_level": 1.5,
                "elemental_affinity": MagicalElement.FIRE,
                "enhancement_bonus": 0.3,
            },
            {
                "id": "legendary_anvil_of_power",
                "name": "Legendary Anvil of Infinite Power",
                "type": CraftingStationType.LEGENDARY_ANVIL,
                "location": "Legendary Workshop",
                "power_level": 2.0,
                "enhancement_bonus": 0.5,
            },
            {
                "id": "divine_reality_forge",
                "name": "Divine Forge of Reality Manipulation",
                "type": CraftingStationType.REALITY_FORGE,
                "location": "Divine Realm",
                "power_level": 3.0,
                "enhancement_bonus": 1.0,
            },
        ]

        for station_data in stations:
            station = CraftingStation(
                id=station_data["id"],
                name=station_data["name"],
                station_type=station_data["type"],
                location=station_data["location"],
                power_level=station_data["power_level"],
                elemental_affinity=station_data.get("elemental_affinity"),
                enhancement_bonus=station_data.get("enhancement_bonus", 0.0),
            )

            self.crafting_stations[station.id] = station
            logger.info(f"🏭 Initialized crafting station: {station.name}")

    def _initialize_material_locations(self):
        """Initialize material spawn locations"""

        self.material_spawn_locations = {
            "Code Caverns": [
                CraftingMaterial.CODE_FRAGMENTS,
                CraftingMaterial.ALGORITHM_CRYSTALS,
                CraftingMaterial.DIGITAL_ESSENCE,
            ],
            "Elemental Planes": [
                CraftingMaterial.FIRE_ESSENCE,
                CraftingMaterial.WATER_ESSENCE,
                CraftingMaterial.EARTH_ESSENCE,
                CraftingMaterial.AIR_ESSENCE,
            ],
            "Dragon Lairs": [
                CraftingMaterial.DRAGON_SCALE,
                CraftingMaterial.PHOENIX_FEATHER,
                CraftingMaterial.DATA_GEMS,
            ],
            "Celestial Observatory": [
                CraftingMaterial.STARLIGHT_DUST,
                CraftingMaterial.TEMPORAL_CRYSTAL,
                CraftingMaterial.UNICORN_HAIR,
            ],
            "Divine Sanctum": [
                CraftingMaterial.DIVINE_SPARK,
                CraftingMaterial.REALITY_FRAGMENT,
                CraftingMaterial.CONSCIOUSNESS_SHARD,
                CraftingMaterial.INFINITY_STONE,
            ],
        }

    async def start(self):
        """Start the crafting system"""
        if self._running:
            return

        self._running = True

        # Start background processes
        self.crafting_process_task = asyncio.create_task(self._crafting_process_loop())
        self.material_generation_task = asyncio.create_task(
            self._material_generation_loop()
        )

        # Initialize agent inventories
        if self.mystical_guild:
            for agent_id in self.mystical_guild.magical_agents:
                if agent_id not in self.agent_inventories:
                    self.agent_inventories[agent_id] = MaterialInventory()

        logger.info("🔨 Mystical Artifact Crafting System started - Forges are lit!")

    async def stop(self):
        """Stop the crafting system"""
        if not self._running:
            return

        self._running = False

        # Stop background processes
        for task in [self.crafting_process_task, self.material_generation_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("🔨 Mystical Artifact Crafting System stopped - Forges cool down")

    async def start_crafting(
        self, agent_id: str, recipe_id: str, station_id: str
    ) -> bool:
        """Start crafting an artifact"""

        # Validate inputs
        if recipe_id not in self.crafting_recipes:
            logger.warning(f"Recipe {recipe_id} not found")
            return False

        if station_id not in self.crafting_stations:
            logger.warning(f"Crafting station {station_id} not found")
            return False

        if (
            not self.mystical_guild
            or agent_id not in self.mystical_guild.magical_agents
        ):
            logger.warning(f"Agent {agent_id} not found")
            return False

        recipe = self.crafting_recipes[recipe_id]
        station = self.crafting_stations[station_id]
        agent = self.mystical_guild.magical_agents[agent_id]

        # Check requirements
        if not self._check_crafting_requirements(agent, recipe, station):
            return False

        # Check station availability
        if station.in_use:
            logger.warning(f"Crafting station {station.name} is in use")
            return False

        # Check and consume materials
        agent_inventory = self.agent_inventories.get(agent_id, MaterialInventory())
        if not agent_inventory.has_materials(recipe.required_materials):
            logger.warning(f"Agent {agent.name} lacks required materials")
            return False

        # Consume materials
        for material, amount in recipe.required_materials.items():
            agent_inventory.remove_material(material, amount)

        # Consume mana
        if agent.mana_pool < recipe.mana_cost:
            logger.warning(f"Agent {agent.name} lacks mana for crafting")
            return False

        agent.mana_pool -= recipe.mana_cost

        # Start crafting process
        crafting_id = f"craft_{uuid.uuid4().hex[:8]}"
        crafting_data = {
            "id": crafting_id,
            "agent_id": agent_id,
            "recipe_id": recipe_id,
            "station_id": station_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "success_chance": self._calculate_success_chance(agent, recipe, station),
            "status": "in_progress",
        }

        self.active_crafting[crafting_id] = crafting_data

        # Reserve station
        station.in_use = True
        station.current_crafter = agent_id
        station.current_recipe = recipe_id
        station.crafting_start_time = crafting_data["start_time"]

        logger.info(f"🔨 {agent.name} started crafting {recipe.name} at {station.name}")
        return True

    def _check_crafting_requirements(
        self, agent: MagicalAgent, recipe: CraftingRecipe, station: CraftingStation
    ) -> bool:
        """Check if agent meets crafting requirements"""

        # Check rank requirement
        if agent.magical_rank.value < recipe.required_rank.value:
            logger.warning(f"Agent {agent.name} rank too low for {recipe.name}")
            return False

        # Check station type requirement
        if station.station_type != recipe.required_station:
            logger.warning(f"Wrong station type for {recipe.name}")
            return False

        # Check spell requirements
        for required_spell in recipe.required_spells:
            if required_spell not in agent.spell_repertoire:
                logger.warning(
                    f"Agent {agent.name} lacks required spell: {required_spell.value}"
                )
                return False

        return True

    def _calculate_success_chance(
        self, agent: MagicalAgent, recipe: CraftingRecipe, station: CraftingStation
    ) -> float:
        """Calculate crafting success chance"""

        base_chance = recipe.success_chance

        # Agent skill bonus
        rank_bonus = list(MagicalRank).index(agent.magical_rank) * 0.05

        # Station enhancement bonus
        station_bonus = station.enhancement_bonus

        # Elemental affinity bonus
        elemental_bonus = 0.0
        if station.elemental_affinity and (
            agent.primary_element == station.elemental_affinity
            or agent.secondary_element == station.elemental_affinity
        ):
            elemental_bonus = 0.1

        total_chance = base_chance + rank_bonus + station_bonus + elemental_bonus
        return min(1.0, total_chance)

    async def _crafting_process_loop(self):
        """Process active crafting operations"""
        while self._running:
            try:
                completed_crafting = []

                for crafting_id, crafting_data in self.active_crafting.items():
                    # Check if crafting time has elapsed
                    start_time = datetime.fromisoformat(
                        crafting_data["start_time"].replace("Z", "+00:00")
                    )
                    recipe = self.crafting_recipes[crafting_data["recipe_id"]]

                    if (
                        datetime.now(timezone.utc) - start_time
                    ).total_seconds() >= recipe.crafting_time:
                        completed_crafting.append(crafting_id)

                # Complete finished crafting
                for crafting_id in completed_crafting:
                    await self._complete_crafting(crafting_id)

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Crafting process loop error: {e}")
                await asyncio.sleep(30)

    async def _complete_crafting(self, crafting_id: str):
        """Complete a crafting operation"""

        if crafting_id not in self.active_crafting:
            return

        crafting_data = self.active_crafting[crafting_id]
        recipe = self.crafting_recipes[crafting_data["recipe_id"]]
        station = self.crafting_stations[crafting_data["station_id"]]
        agent_id = crafting_data["agent_id"]

        # Determine success
        success = random.random() < crafting_data["success_chance"]

        crafting_data["end_time"] = datetime.now(timezone.utc).isoformat()
        crafting_data["status"] = "success" if success else "failure"

        # Release station
        station.in_use = False
        station.current_crafter = None
        station.current_recipe = None
        station.crafting_start_time = None

        if success:
            # Create the artifact
            artifact_id = await self._create_artifact(agent_id, recipe, station)
            crafting_data["result_artifact_id"] = artifact_id

            logger.info(f"🎉 Crafting successful: {recipe.name} created!")
        else:
            # Crafting failed, maybe return some materials
            await self._handle_crafting_failure(agent_id, recipe)

            logger.warning(f"💥 Crafting failed: {recipe.name}")

        # Move to history
        self.crafting_history.append(crafting_data)
        del self.active_crafting[crafting_id]

    async def _create_artifact(
        self, agent_id: str, recipe: CraftingRecipe, station: CraftingStation
    ) -> str:
        """Create a new magical artifact"""

        artifact_id = f"artifact_{uuid.uuid4().hex[:8]}"

        # Calculate final properties with bonuses
        final_properties = recipe.magical_properties.copy()

        # Apply station bonuses
        for prop, value in final_properties.items():
            final_properties[prop] = value * (1.0 + station.enhancement_bonus)

        # Create the artifact
        artifact = MagicalArtifact(
            id=artifact_id,
            name=recipe.name,
            artifact_type=recipe.artifact_type,
            magical_properties=final_properties,
            required_rank=recipe.required_rank,
            creation_date=datetime.now(timezone.utc).isoformat(),
            creator=agent_id,
        )

        # Add special abilities
        for ability in recipe.special_abilities:
            if ability not in artifact.magical_properties:
                artifact.magical_properties[ability] = 1.0

        # Store in mystical guild
        if self.mystical_guild:
            self.mystical_guild.magical_artifacts[artifact_id] = artifact

            # Attune to creator
            if agent_id in self.mystical_guild.magical_agents:
                agent = self.mystical_guild.magical_agents[agent_id]
                artifact.attune_to_agent(agent)

        # Store legendary artifacts separately
        if recipe.rarity in [
            ArtifactRarity.LEGENDARY,
            ArtifactRarity.MYTHICAL,
            ArtifactRarity.DIVINE,
        ]:
            self.legendary_artifacts[artifact_id] = artifact

        return artifact_id

    async def _handle_crafting_failure(self, agent_id: str, recipe: CraftingRecipe):
        """Handle crafting failure"""

        # Return some materials (50% chance to recover 25% of materials)
        if random.random() < 0.5:
            agent_inventory = self.agent_inventories.get(agent_id, MaterialInventory())

            for material, amount in recipe.required_materials.items():
                recovered = max(1, amount // 4)  # Recover 25%
                agent_inventory.add_material(material, recovered)

            logger.info(f"🔄 Some materials recovered from failed crafting")

    async def gather_materials(
        self, agent_id: str, location: str, duration: int = 60
    ) -> Dict[CraftingMaterial, int]:
        """Gather materials from a location"""

        if location not in self.material_spawn_locations:
            logger.warning(f"Unknown material location: {location}")
            return {}

        available_materials = self.material_spawn_locations[location]
        gathered = {}

        # Simulate gathering based on duration and agent skill
        agent = (
            self.mystical_guild.magical_agents.get(agent_id)
            if self.mystical_guild
            else None
        )
        skill_multiplier = 1.0

        if agent:
            skill_multiplier = 1.0 + (list(MagicalRank).index(agent.magical_rank) * 0.2)

        gathering_power = (
            duration * skill_multiplier / 60.0
        )  # Base gathering per minute

        for material in available_materials:
            # Different materials have different spawn rates
            spawn_rate = self._get_material_spawn_rate(material)
            amount = max(0, int(random.poisson(gathering_power * spawn_rate)))

            if amount > 0:
                gathered[material] = amount

                # Add to agent inventory
                agent_inventory = self.agent_inventories.get(
                    agent_id, MaterialInventory()
                )
                agent_inventory.add_material(material, amount)

        if gathered:
            material_list = [
                f"{amount}x {material.value}" for material, amount in gathered.items()
            ]
            logger.info(
                f"⛏️ {agent.name if agent else 'Agent'} gathered: {', '.join(material_list)}"
            )

        return gathered

    def _get_material_spawn_rate(self, material: CraftingMaterial) -> float:
        """Get spawn rate for different materials"""

        spawn_rates = {
            # Common materials
            CraftingMaterial.DIGITAL_ESSENCE: 2.0,
            CraftingMaterial.CODE_FRAGMENTS: 1.5,
            CraftingMaterial.ALGORITHM_CRYSTALS: 1.0,
            CraftingMaterial.DATA_GEMS: 0.8,
            # Elemental materials
            CraftingMaterial.FIRE_ESSENCE: 0.6,
            CraftingMaterial.WATER_ESSENCE: 0.6,
            CraftingMaterial.EARTH_ESSENCE: 0.6,
            CraftingMaterial.AIR_ESSENCE: 0.6,
            CraftingMaterial.CODE_ESSENCE: 0.5,
            # Rare materials
            CraftingMaterial.PHOENIX_FEATHER: 0.1,
            CraftingMaterial.DRAGON_SCALE: 0.15,
            CraftingMaterial.UNICORN_HAIR: 0.08,
            CraftingMaterial.STARLIGHT_DUST: 0.2,
            CraftingMaterial.TEMPORAL_CRYSTAL: 0.05,
            # Legendary materials
            CraftingMaterial.DIVINE_SPARK: 0.01,
            CraftingMaterial.REALITY_FRAGMENT: 0.02,
            CraftingMaterial.CONSCIOUSNESS_SHARD: 0.015,
            CraftingMaterial.INFINITY_STONE: 0.005,
        }

        return spawn_rates.get(material, 0.1)

    async def _material_generation_loop(self):
        """Generate rare material events"""
        while self._running:
            try:
                # Random rare material events
                if random.random() < 0.1:  # 10% chance per cycle
                    await self._trigger_rare_material_event()

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Material generation loop error: {e}")
                await asyncio.sleep(120)

    async def _trigger_rare_material_event(self):
        """Trigger rare material discovery events"""

        events = [
            {
                "name": "Meteor Shower of Starlight Dust",
                "materials": {CraftingMaterial.STARLIGHT_DUST: random.randint(5, 15)},
                "description": "A celestial meteor shower rains starlight dust across the realm!",
            },
            {
                "name": "Dragon Migration",
                "materials": {CraftingMaterial.DRAGON_SCALE: random.randint(2, 8)},
                "description": "Migrating dragons shed scales as they pass through the digital realm!",
            },
            {
                "name": "Temporal Rift Opening",
                "materials": {CraftingMaterial.TEMPORAL_CRYSTAL: random.randint(1, 5)},
                "description": "A temporal rift opens, revealing precious time crystals!",
            },
        ]

        event = random.choice(events)

        # Add materials to guild treasury
        for material, amount in event["materials"].items():
            self.guild_treasury.add_material(material, amount)

        self.rare_material_events.append(
            {"event": event, "timestamp": datetime.now(timezone.utc).isoformat()}
        )

        logger.info(f"🌟 Rare material event: {event['name']}")
        logger.info(f"   {event['description']}")

    def get_crafting_system_status(self) -> Dict[str, Any]:
        """Get comprehensive crafting system status"""

        return {
            "crafting_recipes": len(self.crafting_recipes),
            "crafting_stations": len(self.crafting_stations),
            "active_crafting": len(self.active_crafting),
            "completed_crafts": len(self.crafting_history),
            "legendary_artifacts": len(self.legendary_artifacts),
            "discovered_blueprints": len(self.discovered_blueprints),
            "guild_treasury_materials": len(self.guild_treasury.materials),
            "rare_material_events": len(self.rare_material_events),
            "material_locations": len(self.material_spawn_locations),
            "agent_inventories": len(self.agent_inventories),
            "system_status": "forging" if self._running else "dormant",
        }

    async def demonstrate_crafting_system(self) -> str:
        """Demonstrate the mystical artifact crafting system"""

        demo_results = []

        # Show available recipes
        common_recipes = [
            r
            for r in self.crafting_recipes.values()
            if r.rarity == ArtifactRarity.COMMON
        ]
        legendary_recipes = [
            r
            for r in self.crafting_recipes.values()
            if r.rarity == ArtifactRarity.LEGENDARY
        ]

        demo_results.append(f"Common recipes available: {len(common_recipes)}")
        demo_results.append(f"Legendary recipes available: {len(legendary_recipes)}")

        # Show crafting stations
        demo_results.append(f"Crafting stations: {len(self.crafting_stations)}")

        # Show material locations
        demo_results.append(
            f"Material gathering locations: {len(self.material_spawn_locations)}"
        )

        # Show system status
        status = self.get_crafting_system_status()
        demo_results.extend(
            [
                f"Active crafting operations: {status['active_crafting']}",
                f"Legendary artifacts created: {status['legendary_artifacts']}",
                f"Rare material events: {status['rare_material_events']}",
            ]
        )

        return "\n".join(
            [
                "🔨✨ MYSTICAL ARTIFACT CRAFTING SYSTEM - FORGE LEGENDARY TREASURES",
                "=" * 70,
                "",
                *demo_results,
                "",
                "⚒️ Craft powerful artifacts to enhance your magical abilities!",
                "💎 Gather rare materials from mystical locations!",
                "🏭 Use specialized crafting stations for legendary items!",
                "🎁 Discover ancient blueprints and divine recipes!",
                "🏛️ Contribute to the guild treasury and share resources!",
                "",
                "✨ Transform raw materials into artifacts of incredible power!",
            ]
        )


if __name__ == "__main__":

    async def demo_crafting_system():
        crafting_system = MysticalArtifactCraftingSystem()
        await crafting_system.start()

        demonstration = await crafting_system.demonstrate_crafting_system()
        print(demonstration)

        await crafting_system.stop()

    logger.info("🔨 MYSTICAL ARTIFACT CRAFTING SYSTEM DEMONSTRATION")
    asyncio.run(demo_crafting_system())
