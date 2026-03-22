"""
Override of Evennia's default get command.

Adds fungible support (gold and resources) alongside the existing
object (NFT) pickup. Uses the shared parse_item_args() parser for
standardised syntax across all item commands.

Usage:
    get <obj>                       — pick up an object (NFT)
    get <amount> <fungible>         — pick up gold or a resource
    get all <fungible>              — pick up all of a fungible
    get all                         — pick up everything in the room
    get #<id>                       — pick up an NFT by token ID
    get <obj> [from] <container>    — take from container
    get <amount> gold [from] <container>
    get <amount> <resource> [from] <container>
    get all [from] <container>      — take everything from container

Ownership model (from container): item transitions from container's
current ownership → actor's ownership. Same-owner is a no-op for
the mirror. Different-owner dispatches the appropriate service call.
"""

from django.conf import settings

from evennia.commands.default.general import NumberedTargetCommand
from evennia.objects.objects import DefaultCharacter, DefaultExit
from evennia.utils import utils

from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args
from utils.weight_check import (
    check_can_carry, get_item_weight, get_gold_weight, get_resource_weight,
)

GOLD = settings.GOLD_DISPLAY


class CmdGet(NumberedTargetCommand):
    """
    Pick up something.

    Usage:
        get <obj>
        get <amount> gold
        get <amount> <resource>
        get all gold
        get all <resource>
        get all
        get #<id>
        get <obj> [from] <container>
        get <amount> gold [from] <container>
        get <amount> <resource> [from] <container>
        get all [from] <container>

    Pick up an object, gold, or resources from your location
    or from a container. The word 'from' is optional.
    """

    key = "get"
    aliases = ["grab", "take"]
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            self.msg("Get what?")
            return

        # ---------------------------------------------------------- #
        #  Parse for "from <container>" — take from container
        # ---------------------------------------------------------- #
        lower = self.args.lower()
        idx = lower.rfind(" from ")
        if idx != -1:
            item_part = self.args[:idx].strip()
            container_name = self.args[idx + 6:].strip()
            if item_part and container_name:
                self._get_from_container(caller, item_part, container_name)
                return

        # ---------------------------------------------------------- #
        #  Fallback: try last word as container name
        # ---------------------------------------------------------- #
        container, item_part = self._try_split_container(caller)
        if container:
            self._get_from_container(caller, item_part, container.key)
            return

        # ---------------------------------------------------------- #
        #  Parse args through shared parser
        #  NumberedTargetCommand strips leading numbers: "50 gold" →
        #  self.number=50, self.args="gold". Override amount if needed.
        # ---------------------------------------------------------- #
        parsed = parse_item_args(self.args)
        if not parsed:
            self.msg("Get what?")
            return

        # If NumberedTargetCommand consumed a number and result is fungible,
        # override the default amount with the parsed number.
        if self.number > 0 and parsed.type in ("gold", "resource"):
            parsed = parsed._replace(amount=self.number)

        # ---------------------------------------------------------- #
        #  Dispatch based on parsed type
        # ---------------------------------------------------------- #
        if parsed.type == "all":
            self._get_all(caller)
        elif parsed.type == "gold":
            self._get_fungible_gold(caller, parsed.amount)
        elif parsed.type == "resource":
            self._get_fungible_resource(
                caller, parsed.resource_id, parsed.resource_info, parsed.amount
            )
        elif parsed.type == "token_id":
            self._get_by_token_id(caller, parsed.token_id)
        else:  # type == "item"
            self._get_object(caller, parsed.search_term)

    # ============================================================== #
    #  Try last word as container (no-preposition fallback)
    # ============================================================== #

    def _try_split_container(self, caller):
        """
        Try the last word of args as a container name.

        Returns (container, item_part) or (None, None).
        """
        parts = self.args.rsplit(None, 1)
        if len(parts) < 2:
            return None, None
        item_part, container_word = parts
        # Search for container quietly — no error messages
        container = caller.search(container_word, location=caller, quiet=True)
        if not container:
            container = caller.search(
                container_word, location=caller.location, quiet=True
            )
        if not container:
            return None, None
        if isinstance(container, list):
            container = container[0]
        if not getattr(container, "is_container", False):
            return None, None
        if hasattr(container, "is_open") and not container.is_open:
            return None, None
        return container, item_part.strip()

    # ============================================================== #
    #  Token ID lookup
    # ============================================================== #

    def _get_by_token_id(self, caller, token_id):
        """Pick up an NFT by token ID from the room."""
        room = caller.location
        for obj in room.contents:
            if isinstance(obj, BaseNFTItem) and obj.token_id == token_id:
                if not obj.access(caller, "get"):
                    self.msg(obj.db.get_err_msg or "You can't get that.")
                    return
                if not obj.at_pre_get(caller):
                    return
                ok, msg = check_can_carry(caller, get_item_weight(obj))
                if not ok:
                    self.msg(msg)
                    return
                if obj.move_to(caller, quiet=True, move_type="get"):
                    obj.at_get(caller)
                    obj_name = obj.get_numbered_name(1, caller, return_string=True)
                    caller.location.msg_contents(
                        f"$You() $conj(pick) up {obj_name}.", from_obj=caller,
                    )
                else:
                    self.msg("That can't be picked up.")
                return
        self.msg(f"No item with token ID #{token_id} here.")

    # ============================================================== #
    #  Fungible pickup
    # ============================================================== #

    def _get_fungible_gold(self, caller, amount):
        """Pick up gold from the room."""
        room = caller.location
        if not hasattr(room, "get_gold"):
            self.msg("There's nothing like that here.")
            return

        available = room.get_gold()
        if available <= 0:
            self.msg("There's no gold here.")
            return
        if amount is None:
            amount = available
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        if available < amount:
            self.msg(f"There's only {available} {GOLD['unit']} of {GOLD['name']} here.")
            return

        ok, msg = check_can_carry(caller, get_gold_weight(amount))
        if not ok:
            self.msg(msg)
            return

        room.transfer_gold_to(caller, amount)
        caller.location.msg_contents(
            f"$You() $conj(pick) up {amount} {GOLD['unit']} of {GOLD['name']}.",
            from_obj=caller,
        )

    def _get_fungible_resource(self, caller, resource_id, resource_info, amount):
        """Pick up a resource from the room."""
        room = caller.location
        if not hasattr(room, "get_gold"):
            self.msg("There's nothing like that here.")
            return

        available = room.get_resource(resource_id)
        if available <= 0:
            self.msg(f"There's no {resource_info['name']} here.")
            return
        if amount is None:
            amount = available
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        if available < amount:
            self.msg(
                f"There's only {available} {resource_info['unit']}"
                f" of {resource_info['name']} here."
            )
            return

        ok, msg = check_can_carry(caller, get_resource_weight(resource_id, amount))
        if not ok:
            self.msg(msg)
            return

        room.transfer_resource_to(caller, resource_id, amount)
        caller.location.msg_contents(
            f"$You() $conj(pick) up {amount} {resource_info['unit']}"
            f" of {resource_info['name']}.",
            from_obj=caller,
        )

    # ============================================================== #
    #  "get all" — pick up every object and fungible in the room
    # ============================================================== #

    def _get_all(self, caller):
        """Pick up all objects and fungibles from the room."""
        room = caller.location
        picked_up_anything = False
        skipped_weight = False

        # --- objects (NFTs etc.) ---
        for obj in list(room.contents):
            if obj == caller:
                continue
            if isinstance(obj, (DefaultExit, DefaultCharacter)):
                continue
            if not obj.access(caller, "get"):
                continue
            if not obj.at_pre_get(caller):
                continue
            ok, _ = check_can_carry(caller, get_item_weight(obj))
            if not ok:
                skipped_weight = True
                continue
            if obj.move_to(caller, quiet=True, move_type="get"):
                obj.at_get(caller)
                obj_name = obj.get_numbered_name(1, caller, return_string=True)
                caller.location.msg_contents(
                    f"$You() $conj(pick) up {obj_name}.", from_obj=caller,
                )
                picked_up_anything = True

        # --- fungibles ---
        if hasattr(room, "get_gold"):
            gold = room.get_gold()
            if gold > 0:
                ok, _ = check_can_carry(caller, get_gold_weight(gold))
                if ok:
                    room.transfer_gold_to(caller, gold)
                    caller.location.msg_contents(
                        f"$You() $conj(pick) up {gold} {GOLD['unit']} of {GOLD['name']}.",
                        from_obj=caller,
                    )
                    picked_up_anything = True
                else:
                    skipped_weight = True

            for rid, amt in list(room.get_all_resources().items()):
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if not info:
                        continue
                    ok, _ = check_can_carry(caller, get_resource_weight(rid, amt))
                    if not ok:
                        skipped_weight = True
                        continue
                    room.transfer_resource_to(caller, rid, amt)
                    caller.location.msg_contents(
                        f"$You() $conj(pick) up {amt} {info['unit']}"
                        f" of {info['name']}.",
                        from_obj=caller,
                    )
                    picked_up_anything = True

        if skipped_weight:
            self.msg("You couldn't pick up everything — you're too encumbered.")
        elif not picked_up_anything:
            self.msg("There's nothing here to pick up.")

    # ============================================================== #
    #  Standard object (NFT) pickup
    # ============================================================== #

    def _get_object(self, caller, search_term):
        """Standard Evennia object pickup with fuzzy matching."""
        objs = caller.search(search_term, location=caller.location, stacked=self.number)
        if not objs:
            return
        objs = utils.make_iter(objs)

        if len(objs) == 1 and caller == objs[0]:
            self.msg("You can't get yourself.")
            return

        for obj in objs:
            if not obj.access(caller, "get"):
                if obj.db.get_err_msg:
                    self.msg(obj.db.get_err_msg)
                else:
                    self.msg("You can't get that.")
                return
            if not obj.at_pre_get(caller):
                return
            ok, msg = check_can_carry(caller, get_item_weight(obj))
            if not ok:
                self.msg(msg)
                return

        moved = []
        for obj in objs:
            if obj.move_to(caller, quiet=True, move_type="get"):
                moved.append(obj)
                obj.at_get(caller)

        if not moved:
            self.msg("That can't be picked up.")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.location.msg_contents(
                f"$You() $conj(pick) up {obj_name}.", from_obj=caller,
            )

    # ============================================================== #
    #  Container: "get <item> from <container>"
    # ============================================================== #

    def _get_from_container(self, caller, item_part, container_name):
        """Dispatch 'get ... from ...' for containers."""
        container = self._find_container(caller, container_name)
        if not container:
            return

        parsed = parse_item_args(item_part)
        if not parsed:
            self.msg("Get what?")
            return

        if parsed.type == "all":
            self._get_all_from_container(caller, container)
        elif parsed.type == "gold":
            self._get_gold_from_container(caller, container, parsed.amount)
        elif parsed.type == "resource":
            self._get_resource_from_container(
                caller, container,
                parsed.resource_id, parsed.resource_info, parsed.amount,
            )
        elif parsed.type == "token_id":
            self._get_by_token_id_from_container(
                caller, container, parsed.token_id
            )
        else:  # type == "item"
            self._get_object_from_container(
                caller, container, parsed.search_term
            )

    def _find_container(self, caller, name):
        """Search for a container in caller's inventory and room."""
        container = caller.search(name, location=caller, quiet=True)
        if not container:
            container = caller.search(
                name, location=caller.location, quiet=True,
            )
        if not container:
            caller.msg(f"You don't see '{name}' here.")
            return None

        if isinstance(container, list):
            container = container[0]

        if not getattr(container, "is_container", False):
            caller.msg(f"{container.key} is not a container.")
            return None

        # Gate on open/closed state (chests, etc.)
        if hasattr(container, "is_open") and not container.is_open:
            caller.msg(f"{container.key} is closed.")
            return None

        return container

    # ============================================================== #
    #  NFT by token ID from container
    # ============================================================== #

    def _get_by_token_id_from_container(self, caller, container, token_id):
        """Take an NFT by token ID from a container."""
        for obj in container.contents:
            if isinstance(obj, BaseNFTItem) and obj.token_id == token_id:
                self._do_get_from_container(caller, container, obj)
                return
        caller.msg(
            f"{container.key} doesn't contain an item with token ID #{token_id}."
        )

    # ============================================================== #
    #  NFT by name from container
    # ============================================================== #

    def _get_object_from_container(self, caller, container, search_term):
        """Take an NFT by name from a container."""
        obj = caller.search(
            search_term,
            location=container,
            nofound_string=(
                f"{container.key} doesn't contain '{search_term}'."
            ),
        )
        if not obj:
            return
        obj = utils.make_iter(obj)[0]
        self._do_get_from_container(caller, container, obj)

    # ============================================================== #
    #  Common NFT get-from-container logic
    # ============================================================== #

    def _do_get_from_container(self, caller, container, obj):
        """Validate and take an NFT from a container."""
        ok, msg = check_can_carry(caller, get_item_weight(obj))
        if not ok:
            self.msg(msg)
            return

        if obj.move_to(caller, quiet=True, move_type="get"):
            caller.msg(f"You get {obj.key} from {container.key}.")
            if caller.location:
                caller.location.msg_contents(
                    f"$You() $conj(get) {obj.key} from {container.key}.",
                    from_obj=caller, exclude=[caller],
                )
        else:
            caller.msg(f"You can't get that from {container.key}.")

    # ============================================================== #
    #  Fungible gold from container
    # ============================================================== #

    def _get_gold_from_container(self, caller, container, amount):
        """Take gold from a container."""
        if not hasattr(container, "get_gold"):
            caller.msg(f"{container.key} doesn't hold gold.")
            return

        available = container.get_gold()
        if available <= 0:
            caller.msg(f"There's no gold in {container.key}.")
            return
        if amount is None:
            amount = available
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        if available < amount:
            caller.msg(
                f"{container.key} only has {available} {GOLD['unit']}"
                f" of {GOLD['name']}."
            )
            return

        ok, msg = check_can_carry(caller, get_gold_weight(amount))
        if not ok:
            self.msg(msg)
            return

        self._transfer_fungible_from_container(
            caller, container, "gold", amount=amount,
        )

        caller.msg(
            f"You get {amount} {GOLD['unit']} of {GOLD['name']}"
            f" from {container.key}."
        )

    # ============================================================== #
    #  Fungible resource from container
    # ============================================================== #

    def _get_resource_from_container(self, caller, container,
                                     resource_id, resource_info, amount):
        """Take a resource from a container."""
        if not hasattr(container, "get_resource"):
            caller.msg(f"{container.key} doesn't hold resources.")
            return

        available = container.get_resource(resource_id)
        if available <= 0:
            caller.msg(
                f"There's no {resource_info['name']} in {container.key}."
            )
            return
        if amount is None:
            amount = available
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        if available < amount:
            caller.msg(
                f"{container.key} only has {available} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        ok, msg = check_can_carry(
            caller, get_resource_weight(resource_id, amount)
        )
        if not ok:
            self.msg(msg)
            return

        self._transfer_fungible_from_container(
            caller, container, "resource",
            amount=amount, resource_id=resource_id,
        )

        caller.msg(
            f"You get {amount} {resource_info['unit']}"
            f" of {resource_info['name']} from {container.key}."
        )

    # ============================================================== #
    #  Fungible transfer helper (resolved ownership)
    # ============================================================== #

    def _transfer_fungible_from_container(self, caller, container,
                                          fungible_type, amount=0,
                                          resource_id=None):
        """
        Move fungibles from container to caller with correct mirror dispatch.

        Resolves container ownership. Same-owner = local state only.
        Different-owner = service call + local state.
        """
        source_type, source_owner = BaseNFTItem._resolve_owner(container)
        dest_type = BaseNFTItem._classify(caller)

        if BaseNFTItem._is_same_owner(
            source_type, source_owner, dest_type, caller
        ):
            # Same owner — just move local state, no service call
            if fungible_type == "gold":
                container._remove_gold(amount)
                caller._add_gold(amount)
            else:
                container._remove_resource(resource_id, amount)
                caller._add_resource(resource_id, amount)
        else:
            # Different owner — use standard transfer (handles service call)
            if fungible_type == "gold":
                container.transfer_gold_to(caller, amount)
            else:
                container.transfer_resource_to(
                    caller, resource_id, amount
                )

    # ============================================================== #
    #  "get all from <container>"
    # ============================================================== #

    def _get_all_from_container(self, caller, container):
        """Take everything from a container."""
        got_anything = False
        skipped_weight = False

        # --- NFT items ---
        for obj in list(container.contents):
            ok, msg = check_can_carry(caller, get_item_weight(obj))
            if not ok:
                skipped_weight = True
                continue
            if obj.move_to(caller, quiet=True, move_type="get"):
                caller.msg(f"You get {obj.key} from {container.key}.")
                got_anything = True

        # --- Fungible gold ---
        if hasattr(container, "get_gold"):
            gold = container.get_gold()
            if gold > 0:
                ok, _ = check_can_carry(caller, get_gold_weight(gold))
                if ok:
                    self._transfer_fungible_from_container(
                        caller, container, "gold", amount=gold,
                    )
                    caller.msg(
                        f"You get {gold} {GOLD['unit']} of {GOLD['name']}"
                        f" from {container.key}."
                    )
                    got_anything = True
                else:
                    skipped_weight = True

        # --- Fungible resources ---
        if hasattr(container, "get_all_resources"):
            for rid, amt in list(container.get_all_resources().items()):
                if amt <= 0:
                    continue
                info = get_all_resource_types().get(rid)
                if not info:
                    continue
                ok, _ = check_can_carry(
                    caller, get_resource_weight(rid, amt)
                )
                if not ok:
                    skipped_weight = True
                    continue
                self._transfer_fungible_from_container(
                    caller, container, "resource",
                    amount=amt, resource_id=rid,
                )
                caller.msg(
                    f"You get {amt} {info['unit']}"
                    f" of {info['name']} from {container.key}."
                )
                got_anything = True

        if skipped_weight:
            self.msg(
                "You couldn't get everything — you're too encumbered."
            )
        elif not got_anything:
            self.msg(f"{container.key} is empty.")
