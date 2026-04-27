from typeclasses.terrain.rooms.room_inn import RoomInn


class RoomHarvestMoon(RoomInn):

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if moved_obj.has_account:
            self._check_rat_quest_defeat(moved_obj)

    def _check_rat_quest_defeat(self, character):
        if not hasattr(character, "quests") or not hasattr(character, "hp"):
            return
        if character.hp > 1:
            return
        quest = character.quests.get("rat_cellar")
        if not quest or quest.is_completed:
            return
        character.hp = character.effective_hp_max
        character.msg(
            '\n|yRowan rushes over, concern written across his face. '
            '"Easy there! Let me get you a drink — on the house." '
            "He presses a warm mug into your hands and you feel "
            "strength returning to your limbs.|n\n"
            "|gYou have been fully healed.|n\n"
            '|wRowan says, "Those rats are nastier than I thought. '
            "Take a moment to rest and try again when you're ready.\"|n"
        )
