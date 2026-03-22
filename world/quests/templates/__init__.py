"""
Quest templates — reusable base classes for common quest patterns.

    CollectQuest  — bring N of resource X
    VisitQuest    — enter a tagged room
    MultiStepQuest — ordered sequence of sub-objectives
"""

from world.quests.templates.collect_quest import CollectQuest  # noqa: F401
from world.quests.templates.visit_quest import VisitQuest  # noqa: F401
from world.quests.templates.multi_step_quest import MultiStepQuest  # noqa: F401
