"""
TrainerNPC — guild trainer that trains skills and sells recipes.

Placed in guild rooms. Players interact via commands injected by this NPC's
CmdSet (available to characters in the same room):
    train              — list available skills and costs
    train <skill>      — spend skill points to advance mastery level
    buy recipe         — list recipes for sale
    buy recipe <name>  — purchase a recipe (learns it directly)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npc import BaseNPC


class TrainerNPC(BaseNPC):
    """
    Guild trainer — trains skills and sells recipes.

    Configuration (set per instance via @set or seed script):
        trainable_skills: list of skill key strings this trainer teaches
            e.g. ["battleskills", "bash", "parry"]
        trainable_weapons: list of WeaponType.value strings
            e.g. ["long_sword", "dagger"]
        trainer_class: which character class this trainer serves
            e.g. "warrior" — determines which class skill points are used
        trainer_masteries: dict mapping skill/weapon key to mastery int (1-5)
            e.g. {"battleskills": 5, "bash": 3, "long_sword": 4}
            Determines max teachable level and success chance per skill.
            Skills not in this dict default to BASIC (1).
        recipes_for_sale: dict {recipe_key: gold_cost}
            e.g. {"iron_sword": 50, "iron_shield": 75}
    """

    trainable_skills = AttributeProperty([])
    trainable_weapons = AttributeProperty([])
    trainer_class = AttributeProperty(None)    # e.g. "warrior"
    trainer_masteries = AttributeProperty({})  # {skill_key: mastery_int}
    recipes_for_sale = AttributeProperty({})   # {recipe_key: gold_cost}

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_trainer import TrainerCmdSet
        self.cmdset.add(TrainerCmdSet, persistent=True)
