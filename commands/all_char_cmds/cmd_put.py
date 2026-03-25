"""
Put command — place items or fungibles into a container.

Usage:
    put <item> [in] <container>
    put <amount> gold [in] <container>
    put <amount> <resource> [in] <container>
    put all [in] <container>           (with confirmation)
    put #<id> [in] <container>

Ownership model: item transitions from actor's ownership → container's
current ownership. Same-owner (e.g. inventory → own backpack) is a no-op
for the mirror. Different-owner dispatches the appropriate service call.
"""

from django.conf import settings

from evennia import Command
from evennia.utils import utils

from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args
from utils.weight_check import get_gold_weight, get_resource_weight

GOLD = settings.GOLD_DISPLAY


class CmdPut(Command):
    """
    Place something into a container.

    Usage:
        put <item> [in] <container>
        put <amount> gold [in] <container>
        put <amount> <resource> [in] <container>
        put all [in] <container>
        put #<id> [in] <container>

    Place an object, gold, or resources into a container in your
    inventory or in the room. The word 'in' is optional.
    """

    key = "put"
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Put what where?")
            return

        # ---------------------------------------------------------- #
        #  Split on " in " to separate item spec from container name
        # ---------------------------------------------------------- #
        lower = self.args.lower()
        idx = lower.rfind(" in ")
        if idx != -1:
            item_part = self.args[:idx].strip()
            container_name = self.args[idx + 4:].strip()
            if item_part and container_name:
                container = self._find_container(caller, container_name)
                if not container:
                    return
            else:
                caller.msg("Usage: put <item> [in] <container>")
                return
        else:
            # Fallback: try last word as container name
            container, item_part = self._try_split_container(caller)
            if not container:
                caller.msg("Usage: put <item> [in] <container>")
                return

        # ---------------------------------------------------------- #
        #  Parse the item spec
        # ---------------------------------------------------------- #
        parsed = parse_item_args(item_part)
        if not parsed:
            caller.msg("Put what?")
            return

        # ---------------------------------------------------------- #
        #  Dispatch
        # ---------------------------------------------------------- #
        if parsed.type == "all":
            yield from self._put_all(caller, container)
        elif parsed.type == "gold":
            self._put_fungible_gold(caller, container, parsed.amount)
        elif parsed.type == "resource":
            self._put_fungible_resource(
                caller, container,
                parsed.resource_id, parsed.resource_info, parsed.amount,
            )
        elif parsed.type == "token_id":
            self._put_by_token_id(caller, container, parsed.token_id)
        else:  # type == "item"
            self._put_object(caller, container, parsed.search_term)

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
            caller.msg(f"{container.key} is closed.")
            return None, None
        return container, item_part.strip()

    # ============================================================== #
    #  Find Container
    # ============================================================== #

    def _find_container(self, caller, name):
        """
        Search for a container in caller's inventory and room.
        Returns the container or None (with error message).
        """
        # Search inventory first, then room
        container = caller.search(
            name,
            location=caller,
            quiet=True,
        )
        if not container:
            container = caller.search(
                name,
                location=caller.location,
                quiet=True,
            )
        if not container:
            caller.msg(f"You don't see '{name}' here.")
            return None

        # Handle list results
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
    #  NFT by token ID
    # ============================================================== #

    def _put_by_token_id(self, caller, container, item_id):
        """Put an NFT by item ID into container."""
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                self._do_put_nft(caller, container, obj)
                return
        caller.msg(f"You aren't carrying an item with ID #{item_id}.")

    # ============================================================== #
    #  NFT by name
    # ============================================================== #

    def _put_object(self, caller, container, search_term):
        """Put an NFT by name into container."""
        obj = caller.search(
            search_term,
            location=caller,
            nofound_string=f"You aren't carrying {search_term}.",
        )
        if not obj:
            return
        obj = utils.make_iter(obj)[0]
        self._do_put_nft(caller, container, obj)

    # ============================================================== #
    #  Common NFT put logic
    # ============================================================== #

    def _do_put_nft(self, caller, container, obj):
        """Validate and put an NFT into a container."""
        # Can't put worn items
        if hasattr(caller, "is_worn") and caller.is_worn(obj):
            caller.msg(f"You must remove {obj.key} first.")
            return

        # Capacity check
        ok, msg = container.can_hold_item(obj)
        if not ok:
            caller.msg(msg)
            return

        # Move — at_post_move handles mirror via _resolve_owner
        if obj.move_to(container, quiet=True, move_type="put"):
            caller.msg(f"You put {obj.key} in {container.key}.")
            if caller.location:
                caller.location.msg_contents(
                    f"$You() $conj(put) {obj.key} in {container.key}.",
                    from_obj=caller, exclude=[caller],
                )
        else:
            caller.msg(f"You can't put that in {container.key}.")

    # ============================================================== #
    #  Fungible gold
    # ============================================================== #

    def _put_fungible_gold(self, caller, container, amount):
        """Put gold into container."""
        current = caller.get_gold()
        if current <= 0:
            caller.msg("You don't have any gold.")
            return
        if amount is None:
            amount = current
        if amount <= 0:
            caller.msg("Amount must be positive.")
            return
        if current < amount:
            caller.msg(
                f"You only have {current} {GOLD['unit']} of {GOLD['name']}."
            )
            return

        # Capacity check
        weight = get_gold_weight(amount)
        if not container.can_hold(weight):
            caller.msg(
                f"{container.key} can't hold that much. "
                f"(Available: {container.get_remaining_container_capacity():.1f} kg)"
            )
            return

        # Transfer with resolved ownership
        self._transfer_fungible_to_container(
            caller, container, "gold", amount=amount,
        )

        caller.msg(
            f"You put {amount} {GOLD['unit']} of {GOLD['name']}"
            f" in {container.key}."
        )

    # ============================================================== #
    #  Fungible resource
    # ============================================================== #

    def _put_fungible_resource(self, caller, container,
                               resource_id, resource_info, amount):
        """Put a resource into container."""
        current = caller.get_resource(resource_id)
        if current <= 0:
            caller.msg(f"You don't have any {resource_info['name']}.")
            return
        if amount is None:
            amount = current
        if amount <= 0:
            caller.msg("Amount must be positive.")
            return
        if current < amount:
            caller.msg(
                f"You only have {current} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        weight = get_resource_weight(resource_id, amount)
        if not container.can_hold(weight):
            caller.msg(
                f"{container.key} can't hold that much. "
                f"(Available: {container.get_remaining_container_capacity():.1f} kg)"
            )
            return

        self._transfer_fungible_to_container(
            caller, container, "resource",
            amount=amount, resource_id=resource_id,
        )

        caller.msg(
            f"You put {amount} {resource_info['unit']}"
            f" of {resource_info['name']} in {container.key}."
        )

    # ============================================================== #
    #  Fungible transfer helper (resolved ownership)
    # ============================================================== #

    def _transfer_fungible_to_container(self, caller, container,
                                        fungible_type, amount=0,
                                        resource_id=None):
        """
        Move fungibles from caller into container with correct mirror dispatch.

        Resolves container ownership. Same-owner = local state only.
        Different-owner = service call + local state.
        """
        source_type = BaseNFTItem._classify(caller)
        dest_type, dest_owner = BaseNFTItem._resolve_owner(container)

        if BaseNFTItem._is_same_owner(
            source_type, caller, dest_type, dest_owner
        ):
            # Same owner — just move local state, no service call
            if fungible_type == "gold":
                caller._remove_gold(amount)
                container._add_gold(amount)
            else:
                caller._remove_resource(resource_id, amount)
                container._add_resource(resource_id, amount)
        else:
            # Different owner — use standard transfer (handles service call)
            if fungible_type == "gold":
                caller.transfer_gold_to(container, amount)
            else:
                caller.transfer_resource_to(container, resource_id, amount)

    # ============================================================== #
    #  "put all in <container>" — with confirmation
    # ============================================================== #

    def _put_all(self, caller, container):
        """Put all items and fungibles into container. Requires confirmation."""
        summary_lines = []
        items = [
            obj for obj in caller.contents
            if obj != container and obj != caller
            and not (hasattr(caller, "is_worn") and caller.is_worn(obj))
            and not getattr(obj, "is_container", False)
        ]
        if items:
            summary_lines.append(f"  {len(items)} item(s)")
        if hasattr(caller, "get_gold") and caller.get_gold() > 0:
            summary_lines.append(
                f"  {caller.get_gold()} {GOLD['unit']} of {GOLD['name']}"
            )
        if hasattr(caller, "get_all_resources"):
            for rid, amt in caller.get_all_resources().items():
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if info:
                        summary_lines.append(
                            f"  {amt} {info['unit']} of {info['name']}"
                        )

        if not summary_lines:
            caller.msg("You have nothing to put in there.")
            return

        answer = yield (
            f"\nYou are about to put everything into {container.key}:"
            f"\n" + "\n".join(summary_lines)
            + f"\n\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Cancelled.")
            return

        put_anything = False

        # --- NFT items ---
        for obj in list(caller.contents):
            if obj == caller or obj == container:
                continue
            if hasattr(caller, "is_worn") and caller.is_worn(obj):
                continue
            if getattr(obj, "is_container", False):
                continue
            ok, _msg = container.can_hold_item(obj)
            if not ok:
                caller.msg(f"Skipped {obj.key} — {container.key} is full.")
                break
            if obj.move_to(container, quiet=True, move_type="put"):
                caller.msg(f"You put {obj.key} in {container.key}.")
                put_anything = True

        # --- Fungibles ---
        if hasattr(caller, "get_gold"):
            gold = caller.get_gold()
            if gold > 0:
                weight = get_gold_weight(gold)
                if container.can_hold(weight):
                    self._transfer_fungible_to_container(
                        caller, container, "gold", amount=gold,
                    )
                    caller.msg(
                        f"You put {gold} {GOLD['unit']} of {GOLD['name']}"
                        f" in {container.key}."
                    )
                    put_anything = True

            for rid, amt in list(caller.get_all_resources().items()):
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if not info:
                        continue
                    weight = get_resource_weight(rid, amt)
                    if container.can_hold(weight):
                        self._transfer_fungible_to_container(
                            caller, container, "resource",
                            amount=amt, resource_id=rid,
                        )
                        caller.msg(
                            f"You put {amt} {info['unit']}"
                            f" of {info['name']} in {container.key}."
                        )
                        put_anything = True

        if not put_anything:
            caller.msg("Nothing was put in the container.")
