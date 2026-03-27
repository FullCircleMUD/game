"""
SpawnService — orchestrator for the unified spawn system.

For each SPAWN_CONFIG entry: runs calculator → distributor.
Manages BudgetState per item. Called hourly by UnifiedSpawnScript.

Exposes allocate_quest_reward() for quest system integration and
get_spawn_service() as a module-level accessor.
"""

import logging

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.calculators.resource import ResourceCalculator
from blockchain.xrpl.services.spawn.calculators.gold import GoldCalculator
from blockchain.xrpl.services.spawn.calculators.knowledge import KnowledgeCalculator
from blockchain.xrpl.services.spawn.calculators.rare_nft import RareNFTCalculator
from blockchain.xrpl.services.spawn.distributors.fungible import (
    ResourceDistributor,
    GoldDistributor,
)
from blockchain.xrpl.services.spawn.distributors.nft import (
    ScrollDistributor,
    RecipeDistributor,
    RareNFTDistributor,
)

logger = logging.getLogger("evennia")

# Module-level singleton reference (set by UnifiedSpawnScript).
_spawn_service_instance = None


def get_spawn_service():
    """Get the running SpawnService instance.

    Returns None if the service hasn't been initialized yet.
    Used by the quest system to register quest debt.
    """
    return _spawn_service_instance


def set_spawn_service(instance):
    """Set the module-level SpawnService singleton.

    Called by UnifiedSpawnScript when it starts.
    """
    global _spawn_service_instance
    _spawn_service_instance = instance


# Map calculator name → class
CALCULATOR_CLASSES = {
    "resource": ResourceCalculator,
    "gold": GoldCalculator,
    "knowledge": KnowledgeCalculator,
    "rare_nft": RareNFTCalculator,
}

# Map (calculator_name, category_hint) → distributor instance
# category_hint derived from config or item_type
DISTRIBUTOR_MAP = {
    "resource": ResourceDistributor,
    "gold": GoldDistributor,
    "scroll": ScrollDistributor,
    "recipe": RecipeDistributor,
    "rare_nft": RareNFTDistributor,
}


class SpawnService:
    """Orchestrates calculators and distributors for all spawn config entries."""

    def __init__(self, config):
        """
        Args:
            config: The full SPAWN_CONFIG dict.
        """
        self.config = config
        self.budget_states = {}  # {(item_type, type_key): BudgetState}

        # Populate knowledge entries from spell/recipe registries
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config
        populate_knowledge_config(config)

        # Instantiate calculators (one per type, shared across items)
        self._calculators = {
            name: cls(config) for name, cls in CALCULATOR_CLASSES.items()
        }

        # Instantiate distributors (one per category, reused)
        self._distributors = {
            name: cls() for name, cls in DISTRIBUTOR_MAP.items()
        }

    def run_hourly_cycle(self):
        """Run the full hourly spawn cycle for all configured items.

        For each entry in SPAWN_CONFIG:
        1. Run the calculator to get the hourly budget
        2. Reset or create BudgetState
        3. Pass to the distributor for drip-feed scheduling
        """
        summary = []

        for (item_type, type_key), cfg in self.config.items():
            calculator_name = cfg.get("calculator")
            if not calculator_name:
                continue

            calculator = self._calculators.get(calculator_name)
            if not calculator:
                logger.warning(
                    f"SpawnService: unknown calculator '{calculator_name}' "
                    f"for ({item_type}, {type_key})"
                )
                continue

            # Calculate budget
            try:
                budget = calculator.calculate(item_type, type_key)
            except KeyError:
                logger.warning(
                    f"SpawnService: no config for ({item_type}, {type_key})"
                )
                continue
            except Exception:
                logger.log_trace(
                    f"SpawnService: calculator error for ({item_type}, {type_key})"
                )
                continue

            if budget <= 0:
                continue

            # Get or create budget state
            state_key = (item_type, type_key)
            if state_key not in self.budget_states:
                self.budget_states[state_key] = BudgetState(
                    item_type=item_type, type_key=type_key,
                )
            bs = self.budget_states[state_key]
            bs.reset_for_hour(budget)

            # Get distributor
            distributor = self._get_distributor(item_type, type_key)
            if not distributor:
                logger.warning(
                    f"SpawnService: no distributor for ({item_type}, {type_key})"
                )
                continue

            # Schedule distribution
            distributor.distribute(type_key, bs)
            summary.append(f"{item_type}/{type_key}={budget}")

        if summary:
            logger.info(f"SpawnService: {', '.join(summary)}")
        else:
            logger.info("SpawnService: no items budgeted this cycle")

    def _get_distributor(self, item_type, type_key):
        """Look up the correct distributor for an item.

        Returns a BaseDistributor instance or None.
        """
        if item_type == "resource":
            return self._distributors.get("resource")
        elif item_type == "gold":
            return self._distributors.get("gold")
        elif item_type == "knowledge":
            # Determine scroll vs recipe from the type_key prefix
            if str(type_key).startswith("scroll_"):
                return self._distributors.get("scroll")
            elif str(type_key).startswith("recipe_"):
                return self._distributors.get("recipe")
        elif item_type == "rare_nft":
            return self._distributors.get("rare_nft")
        return None

    def allocate_quest_reward(self, category, key, amount):
        """Register quest reward debt against an item's budget.

        Called by FCMQuest.complete() after awarding rewards.
        Adds debt that will be deducted from future spawn ticks.

        Args:
            category: "resources", "gold", "scrolls", "recipes", "nfts"
            key: resource_id (as str), "gold", or item_type_name
            amount: int — amount awarded to player

        Returns:
            True if debt was registered, False if budget state not found
        """
        # Map category to (item_type, type_key)
        item_type, type_key = self._resolve_category_key(category, key)

        state_key = (item_type, type_key)
        bs = self.budget_states.get(state_key)

        if bs is None:
            # Service hasn't run yet or item not in config — create one
            # to bank the debt for the first cycle
            bs = BudgetState(item_type=item_type, type_key=type_key)
            self.budget_states[state_key] = bs

        bs.add_quest_debt(amount)
        return True

    @staticmethod
    def _resolve_category_key(category, key):
        """Map quest reward category/key to SPAWN_CONFIG (item_type, type_key).

        Args:
            category: "resources", "gold", "scrolls", "recipes", "nfts"
            key: resource_id string, "gold", or item_type_name

        Returns:
            (item_type, type_key) tuple
        """
        if category == "resources":
            return ("resource", int(key))
        elif category == "gold":
            return ("gold", "gold")
        elif category in ("scrolls", "recipes"):
            return ("knowledge", key)
        elif category == "nfts":
            return ("rare_nft", key)
        return (category, key)
