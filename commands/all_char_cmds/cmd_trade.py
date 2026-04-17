"""
Player-to-player trade system.

Safe, atomic item+gold swaps between two players in the same room.
Inspired by the Evennia barter contrib but rewritten for FCM's
gold/item/NFT systems.

Usage:
    trade <player>                — initiate a trade
    trade <player> accept         — accept a trade invitation
    trade <player> decline        — decline a trade invitation

Once in a trade session:
    offer <item1>, <item2> [and <amount> gold]
    accept                        — accept the current deal
    decline                       — retract your acceptance
    status                        — view current offers
    end trade                     — abort the trade
"""

import re

from django.conf import settings

from evennia import CmdSet, DefaultScript
from evennia.commands.command import Command

from commands.command import FCMCommandMixin
from typeclasses.actors.character import FCMCharacter
from utils.weight_check import check_can_carry, get_item_weight, get_gold_weight

GOLD = settings.GOLD_DISPLAY
TRADE_TIMEOUT = 60  # seconds before invitation expires


# ================================================================== #
#  TradeHandler — state machine for an active trade
# ================================================================== #

class TradeHandler:
    """Manages the state of a trade between two parties."""

    def __init__(self, part_a, part_b):
        self.part_a = part_a
        self.part_b = part_b
        self.trade_started = False
        self.part_a_offers = []
        self.part_b_offers = []
        self.part_a_gold = 0
        self.part_b_gold = 0
        self.part_a_accepted = False
        self.part_b_accepted = False
        # Store handler on initiator and add trade cmdset
        part_a.ndb.tradehandler = self
        part_a.cmdset.add(CmdSetTrade)

    def get_other(self, party):
        """Return the other party."""
        if party == self.part_a:
            return self.part_b
        return self.part_a

    def join(self, part_b):
        """Part B accepts the trade invitation."""
        self.trade_started = True
        part_b.ndb.tradehandler = self
        part_b.cmdset.add(CmdSetTrade)

    def unjoin(self):
        """Part B declines the invitation."""
        self.finish(force=True)

    def offer(self, party, items, gold=0):
        """Set a party's offer. Resets both acceptances."""
        if party == self.part_a:
            self.part_a_offers = list(items)
            self.part_a_gold = gold
        else:
            self.part_b_offers = list(items)
            self.part_b_gold = gold
        self.part_a_accepted = False
        self.part_b_accepted = False

    def accept(self, party):
        """Party accepts the current deal. Returns True if trade completes."""
        if party == self.part_a:
            self.part_a_accepted = True
        else:
            self.part_b_accepted = True
        if self.part_a_accepted and self.part_b_accepted:
            return self.finish()
        return False

    def decline(self, party):
        """Party retracts acceptance. Returns True if they had accepted."""
        if party == self.part_a:
            was = self.part_a_accepted
            self.part_a_accepted = False
        else:
            was = self.part_b_accepted
            self.part_b_accepted = False
        return was

    def finish(self, force=False):
        """Execute the trade and clean up.

        If both parties accepted and trade started, move items and gold.
        If force=True, clean up without moving anything.
        Returns True if trade completed successfully.
        """
        completed = False

        if (
            not force
            and self.trade_started
            and self.part_a_accepted
            and self.part_b_accepted
        ):
            # ── Validate weight ──
            a_weight = sum(get_item_weight(o) for o in self.part_b_offers)
            a_weight += get_gold_weight(self.part_b_gold)
            ok_a, _ = check_can_carry(self.part_a, a_weight)

            b_weight = sum(get_item_weight(o) for o in self.part_a_offers)
            b_weight += get_gold_weight(self.part_a_gold)
            ok_b, _ = check_can_carry(self.part_b, b_weight)

            if not ok_a or not ok_b:
                who = self.part_a.key if not ok_a else self.part_b.key
                self.part_a.msg(f"Trade failed: {who} can't carry that much.")
                self.part_b.msg(f"Trade failed: {who} can't carry that much.")
                self.part_a_accepted = False
                self.part_b_accepted = False
                return False

            # ── Move items ──
            for obj in self.part_a_offers:
                obj.move_to(self.part_b, quiet=True, move_type="give")
            for obj in self.part_b_offers:
                obj.move_to(self.part_a, quiet=True, move_type="give")

            # ── Transfer gold ──
            if self.part_a_gold > 0:
                self.part_a.transfer_gold_to(self.part_b, self.part_a_gold)
            if self.part_b_gold > 0:
                self.part_b.transfer_gold_to(self.part_a, self.part_b_gold)

            completed = True

        if completed or force:
            self._cleanup()
            return completed

        return False

    def _cleanup(self):
        """Remove trade state from both parties."""
        self.part_a.cmdset.delete("CmdSetTrade")
        self.part_b.cmdset.delete("CmdSetTrade")
        self.part_a.scripts.stop("trade_request_timeout")
        if hasattr(self.part_a.ndb, "tradehandler"):
            del self.part_a.ndb.tradehandler
        if hasattr(self.part_b.ndb, "tradehandler"):
            del self.part_b.ndb.tradehandler


# ================================================================== #
#  TradeTimeout script
# ================================================================== #

class TradeTimeout(DefaultScript):
    """Times out a trade invitation after TRADE_TIMEOUT seconds."""

    def at_script_creation(self):
        self.key = "trade_request_timeout"
        self.interval = TRADE_TIMEOUT
        self.start_delay = True
        self.repeats = 1
        self.persistent = False

    def at_repeat(self):
        handler = self.obj.ndb.tradehandler
        if handler and not handler.trade_started:
            other = handler.get_other(self.obj)
            self.obj.msg("Trade invitation timed out.")
            other.msg("Trade invitation timed out.")
            handler.finish(force=True)

    def is_valid(self):
        handler = self.obj.ndb.tradehandler
        return handler is not None and not handler.trade_started


# ================================================================== #
#  CmdTrade — initiation command (globally available)
# ================================================================== #

class CmdTrade(FCMCommandMixin, Command):
    """
    Initiate, accept, or decline a trade with another player.

    Usage:
        trade <player>
        trade <player> accept
        trade <player> decline
    """

    key = "trade"
    aliases = []
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def parse(self):
        self.args = self.args.strip()
        self.accept_mode = False
        self.decline_mode = False
        self.target_name = self.args

        if self.args.endswith(" accept"):
            self.accept_mode = True
            self.target_name = self.args[:-7].strip()
        elif self.args.endswith(" decline"):
            self.decline_mode = True
            self.target_name = self.args[:-8].strip()

    def func(self):
        caller = self.caller

        if not self.target_name:
            caller.msg("Usage: trade <player> [accept|decline]")
            return

        # Combat gate
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't trade while in combat!")
            return

        # Find target
        target = caller.search(self.target_name)
        if not target:
            return

        if not isinstance(target, FCMCharacter):
            caller.msg("You can only trade with other players.")
            return

        if target == caller:
            caller.msg("You can't trade with yourself.")
            return

        if target.location != caller.location:
            caller.msg("They're not in the same room as you.")
            return

        # ── Accept invitation ──
        if self.accept_mode:
            handler = target.ndb.tradehandler
            if not handler or handler.part_b != caller or handler.trade_started:
                caller.msg(f"{target.key} hasn't invited you to trade.")
                return
            if caller.ndb.tradehandler and caller.ndb.tradehandler.trade_started:
                caller.msg("You're already in a trade.")
                return
            handler.join(caller)
            caller.msg(f"You accept the trade with {target.key}. Use |woffer|n to make an offer.")
            target.msg(f"{caller.key} accepts your trade. Use |woffer|n to make an offer.")
            caller.location.msg_contents(
                f"{caller.key} and {target.key} begin trading.",
                exclude=[caller, target],
            )
            return

        # ── Decline invitation ──
        if self.decline_mode:
            handler = target.ndb.tradehandler
            if not handler or handler.part_b != caller or handler.trade_started:
                caller.msg(f"{target.key} hasn't invited you to trade.")
                return
            caller.msg(f"You decline the trade with {target.key}.")
            target.msg(f"{caller.key} declines your trade invitation.")
            handler.unjoin()
            return

        # ── Initiate new trade ──
        if caller.ndb.tradehandler:
            if caller.ndb.tradehandler.trade_started:
                caller.msg("You're already in a trade. Use |wend trade|n to abort first.")
            else:
                caller.msg("You already have a pending trade invitation.")
            return

        # Check if target already invited us (reverse initiation = auto-accept)
        handler = target.ndb.tradehandler
        if handler and handler.part_b == caller and not handler.trade_started:
            handler.join(caller)
            caller.msg(f"You accept the trade with {target.key}. Use |woffer|n to make an offer.")
            target.msg(f"{caller.key} accepts your trade. Use |woffer|n to make an offer.")
            caller.location.msg_contents(
                f"{caller.key} and {target.key} begin trading.",
                exclude=[caller, target],
            )
            return

        if target.ndb.tradehandler:
            caller.msg(f"{target.key} is already in a trade.")
            return

        # Create new trade
        TradeHandler(caller, target)
        caller.scripts.add(TradeTimeout, autostart=True)
        caller.msg(
            f"You invite {target.key} to trade. Waiting for their response..."
        )
        target.msg(
            f"{caller.key} wants to trade with you.\n"
            f"Type |wtrade {caller.key} accept|n or |wtrade {caller.key} decline|n."
        )


# ================================================================== #
#  Trade-mode commands (added via CmdSetTrade)
# ================================================================== #

class CmdTradeBase(FCMCommandMixin, Command):
    """Base for trade-session commands."""

    locks = "cmd:all()"
    help_category = "Trading"

    def parse(self):
        self.args = self.args.strip()
        self.handler = self.caller.ndb.tradehandler

    def _guard(self):
        """Check trade is active. Returns False if caller should stop."""
        if not self.handler or not self.handler.trade_started:
            self.caller.msg("You're not in an active trade.")
            return False
        return True


class CmdOffer(CmdTradeBase):
    """
    Make or revise your offer.

    Usage:
        offer <item1>, <item2>, ... [and <amount> gold]
        offer <amount> gold
    """

    key = "offer"

    def func(self):
        if not self._guard():
            return
        caller = self.caller
        handler = self.handler

        if not self.args:
            caller.msg("Offer what? Usage: offer <item> [and <amount> gold]")
            return

        # ── Parse gold clause ──
        gold = 0
        item_part = self.args

        # Check for "and X gold" at the end
        gold_match = re.search(r'\band\s+(\d+)\s+gold\s*$', self.args, re.IGNORECASE)
        if gold_match:
            gold = int(gold_match.group(1))
            item_part = self.args[:gold_match.start()].strip().rstrip(",").strip()
        else:
            # Check for standalone "X gold"
            gold_only = re.match(r'^(\d+)\s+gold\s*$', self.args, re.IGNORECASE)
            if gold_only:
                gold = int(gold_only.group(1))
                item_part = ""

        # ── Validate gold ──
        if gold > 0:
            if not caller.has_gold(gold):
                caller.msg(f"You don't have {gold} {GOLD['unit']} of {GOLD['name']}.")
                return

        # ── Parse item names ──
        items = []
        if item_part:
            item_names = [n.strip() for n in item_part.split(",") if n.strip()]
            for name in item_names:
                obj = caller.search(
                    name, location=caller,
                    nofound_string=f"You aren't carrying '{name}'.",
                )
                if not obj:
                    return
                if caller.is_worn(obj):
                    caller.msg(f"You must remove {obj.key} first.")
                    return
                if hasattr(obj, "at_pre_give") and not obj.at_pre_give(caller, handler.get_other(caller)):
                    return
                items.append(obj)

        if not items and gold == 0:
            caller.msg("You must offer at least one item or some gold.")
            return

        # ── Set the offer ──
        handler.offer(caller, items, gold=gold)
        other = handler.get_other(caller)

        # Build offer description
        parts = []
        if items:
            parts.append(", ".join(o.get_display_name(caller) for o in items))
        if gold > 0:
            parts.append(f"{gold} {GOLD['name']}")
        offer_str = " and ".join(parts)

        caller.msg(f"You offer: {offer_str}")
        other.msg(f"{caller.key} offers: {offer_str}")
        other.msg("Type |waccept|n to agree, or make a counter-offer with |woffer|n.")


class CmdTradeAccept(CmdTradeBase):
    """
    Accept the current trade deal.

    Both parties must accept for the trade to complete.
    Any new offer resets both acceptances.

    Usage:
        accept
    """

    key = "accept"
    aliases = []

    def func(self):
        if not self._guard():
            return
        caller = self.caller
        handler = self.handler
        other = handler.get_other(caller)

        result = handler.accept(caller)
        if result:
            # Trade completed
            # Build summary for both parties
            a_items = ", ".join(o.get_display_name(caller) for o in (handler.part_a_offers or []))
            b_items = ", ".join(o.get_display_name(caller) for o in (handler.part_b_offers or []))

            caller.msg("|gTrade complete!|n")
            other.msg("|gTrade complete!|n")
            caller.location.msg_contents(
                f"{handler.part_a.key} and {handler.part_b.key} complete a trade.",
                exclude=[handler.part_a, handler.part_b],
            )
        else:
            caller.msg("You accept the current offer. Waiting for the other party...")
            other.msg(f"{caller.key} accepts the offer. Type |waccept|n to finalise the trade.")


class CmdTradeDecline(CmdTradeBase):
    """
    Retract your acceptance of the current offer.

    Usage:
        decline
    """

    key = "decline"

    def func(self):
        if not self._guard():
            return
        caller = self.caller
        handler = self.handler
        other = handler.get_other(caller)

        was_accepted = handler.decline(caller)
        if was_accepted:
            caller.msg("You retract your acceptance.")
            other.msg(f"{caller.key} retracts their acceptance.")
        else:
            caller.msg("You haven't accepted anything yet.")


class CmdTradeStatus(CmdTradeBase):
    """
    View current offers from both sides.

    Usage:
        status
    """

    key = "status"
    aliases = ["offers", "deal"]

    def func(self):
        if not self._guard():
            return
        caller = self.caller
        handler = self.handler

        lines = ["|w=== Trade Status ===|n"]

        for party, offers, gold, accepted in [
            (handler.part_a, handler.part_a_offers, handler.part_a_gold, handler.part_a_accepted),
            (handler.part_b, handler.part_b_offers, handler.part_b_gold, handler.part_b_accepted),
        ]:
            label = "You" if party == caller else party.key
            status = "|gAccepted|n" if accepted else "|rPending|n"
            lines.append(f"\n{label} ({status}):")
            if offers:
                for obj in offers:
                    lines.append(f"  - {obj.get_display_name(caller)}")
            if gold > 0:
                lines.append(f"  - {gold} {GOLD['name']}")
            if not offers and gold == 0:
                lines.append("  (nothing offered)")

        caller.msg("\n".join(lines))


class CmdEndTrade(CmdTradeBase):
    """
    Abort the trade. No items or gold change hands.

    Usage:
        end trade
    """

    key = "end trade"
    aliases = ["finish trade", "cancel trade"]

    def func(self):
        if not self._guard():
            return
        caller = self.caller
        handler = self.handler
        other = handler.get_other(caller)

        caller.msg("You end the trade. No items were exchanged.")
        other.msg(f"{caller.key} ends the trade. No items were exchanged.")
        handler.finish(force=True)


# ================================================================== #
#  CmdSetTrade — added to both parties during active trade
# ================================================================== #

class CmdSetTrade(CmdSet):
    """Trade-session commands, added temporarily during a trade."""

    key = "CmdSetTrade"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdOffer())
        self.add(CmdTradeAccept())
        self.add(CmdTradeDecline())
        self.add(CmdTradeStatus())
        self.add(CmdEndTrade())
