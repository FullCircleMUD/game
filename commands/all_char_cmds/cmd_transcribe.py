"""
Transcribe command — consume a spell scroll NFT to learn a spell.

Usage:
    transcribe <scroll>

The spell scroll is consumed (returned to game reserve) on success.
All validation (spell exists, school mastery, already known) is
handled by SpellbookMixin.learn_spell().
"""

from evennia import Command

from typeclasses.items.consumables.spell_scroll_nft_item import SpellScrollNFTItem


class CmdTranscribe(Command):
    """
    Transcribe a spell scroll to learn its spell permanently.

    Usage:
        transcribe <scroll>

    Examples:
        transcribe scroll
        transcribe magic missile scroll

    The spell scroll is consumed when successfully transcribed.
    """

    key = "transcribe"
    aliases = ["tr", "tra", "tran", "trans"]
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Transcribe what? Usage: transcribe <scroll>")
            return

        # Search inventory for SpellScrollNFTItem matching the args
        candidates = [
            obj for obj in caller.contents
            if isinstance(obj, SpellScrollNFTItem)
        ]

        if not candidates:
            caller.msg("You aren't carrying any spell scrolls.")
            return

        item = caller.search(
            self.args.strip(),
            candidates=candidates,
            quiet=True,
        )

        if not item:
            caller.msg("You don't have a spell scroll by that name.")
            return

        # handle list vs single result
        if isinstance(item, list):
            if len(item) > 1:
                names = ", ".join(f"{o.key} (#{o.token_id})" for o in item)
                caller.msg(f"Which scroll? {names}")
                return
            item = item[0]

        # Confirm — consuming the NFT is irreversible
        answer = yield (
            f"\n|y--- Transcribe Spell ---|n"
            f"\nYou are about to transcribe: |w{item.key}|n (#{item.token_id})"
            f"\nThe spell scroll will be consumed."
            f"\n\nProceed? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Transcription cancelled.")
            return

        # Consume — at_consume delegates to learn_spell, then deletes on success
        success, msg = item.consume(caller)
        caller.msg(msg)
