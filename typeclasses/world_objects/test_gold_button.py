"""
TestGoldButton — a big red button that pays the presser gold. Test-only.

**Never place one in a live zone.** A press mints gold out of the vault
reserve with nothing given up in return; in a live zone that is an
uncapped inflation tap.

Companion to the test dispensers in
``typeclasses/actors/npcs/test_dispenser.py``. Those hand out items and
resources for free; this funds the gold side, so a tester can exercise a
real AMM-priced shop without grinding for a purse first.

Modelled on ``XPButton`` (``typeclasses/world_objects/xp_button.py``),
which is the same idea for experience.

Naming is load-bearing. The CI guard in fcm-world
(``.github/workflows/no-test-world-on-main.yml``) rejects any YAML naming
a typeclass module matching ``typeclasses.*.test_*``, which is what keeps
test-only content off main. **A test-only typeclass module must be named
with a `test_` prefix, and must not be renamed away from one.**

The payout goes through ``receive_gold_from_reserve`` — the encapsulated
route on ``FungibleInventoryMixin`` — so the vault mirror and the
character's local balance move together. Never adjust gold with
``_add_gold`` here; that would update Evennia state while leaving the
mirror behind, which is exactly the desync the encapsulation layer exists
to prevent.

It runs synchronously rather than in a worker thread, unlike a shop
purchase. That is safe because ``GoldService.craft_output`` resolves to a
plain Django transaction against the mirror DB — there is no XRPL round
trip to keep off the reactor.
"""

from evennia import AttributeProperty, CmdSet, Command

from enums.size import Size
from typeclasses.world_objects.base_fixture import WorldFixture


class CmdPressGoldButton(Command):
    """
    Press the gold button.

    Usage:
        press gold
        press button
    """

    key = "press"
    aliases = ["press button", "push button", "push", "press gold", "push gold"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        amount = self.obj.gold_amount

        if amount <= 0:
            caller.msg("|rYou press the button. Nothing happens.|n")
            return

        try:
            caller.receive_gold_from_reserve(amount)
        except Exception as err:
            # Most likely the vault reserve is short. Say so plainly
            # rather than leaving the tester wondering.
            caller.msg(f"|rThe button clunks and rejects your hand.|n ({err})")
            return

        caller.msg(
            f"|yYou slam your palm onto the big gold button.|n\n"
            f"|wA cascade of coins clatters into the tray — {amount} gold.|n\n"
            f"You now have {caller.get_gold()} gold."
        )
        caller.location.msg_contents(
            "$You() $conj(slam) a palm onto the big gold button, and coins "
            "clatter into the tray.",
            from_obj=caller,
            exclude=[caller],
        )


class CmdSetGoldButton(CmdSet):
    key = "GoldButtonCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdPressGoldButton())


class TestGoldButton(WorldFixture):
    """A button that pays out gold on every press. Test-only.

    ``gold_amount`` is authored in YAML, so one button can hand out
    pocket change and another a fortune without a code change.
    """

    size = AttributeProperty(Size.TINY.value)
    gold_amount = AttributeProperty(1000)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetGoldButton, persistent=True)
        self.locks.add("call:true()")
