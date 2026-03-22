from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.inn.cmdset_inn import CmdSetInn


class RoomInn(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

    max_height = AttributeProperty(0)
    max_depth = AttributeProperty(0)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetInn, persistent=True)

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Called when something enters the room."""
        super().at_object_receive(moved_obj, source_location, **kwargs)

        if moved_obj.has_account:
            moved_obj.msg("\n|c--- Welcome to the Inn ---|n")
            self._check_rat_quest_defeat(moved_obj)

    def _check_rat_quest_defeat(self, character):
        """Heal a player who was just defeated in the rat cellar quest."""
        if not hasattr(character, "quests") or not hasattr(character, "hp"):
            return
        if character.hp > 1:
            return
        quest = character.quests.get("rat_cellar")
        if not quest or quest.is_completed:
            return
        # Defeated in the rat cellar — bartender heals them
        character.hp = character.effective_hp_max
        character.msg(
            '\n|yRowan rushes over, concern written across his face. '
            '"Easy there! Let me get you a drink \u2014 on the house." '
            "He presses a warm mug into your hands and you feel "
            "strength returning to your limbs.|n\n"
            "|gYou have been fully healed.|n\n"
            '|wRowan says, "Those rats are nastier than I thought. '
            "Take a moment to rest and try again when you're ready.\"|n"
        )
