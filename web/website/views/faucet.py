"""
Faucet page — dispense FakeRLUSD for testnet subscription payments.

Only accessible when IS_TESTNET is True. Redirects to home on mainnet.

Two actions:
  - "trustline" — creates a Xaman TrustSet payload so the user can
    set up a FakeRLUSD trust line (required before receiving tokens).
  - "faucet" (default) — sends 20 FakeRLUSD to the user's wallet.
"""

import re
import logging

from django.conf import settings
from django.shortcuts import redirect, render
from django.views import View

logger = logging.getLogger("evennia")

# XRPL r-address: starts with 'r', 25-35 base58 characters
_RADDRESS_RE = re.compile(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$")


class FaucetView(View):
    template_name = "website/faucet.html"

    def get(self, request):
        if not getattr(settings, "IS_TESTNET", False):
            return redirect("/")
        ctx = {
            "issuer_address": getattr(
                settings, "SUBSCRIPTION_CURRENCY_ISSUER", ""
            ),
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        if not getattr(settings, "IS_TESTNET", False):
            return redirect("/")

        action = request.POST.get("action", "faucet")
        ctx = {
            "issuer_address": getattr(
                settings, "SUBSCRIPTION_CURRENCY_ISSUER", ""
            ),
        }

        if action == "trustline":
            return self._handle_trustline(request, ctx)
        return self._handle_faucet(request, ctx)

    def _handle_trustline(self, request, ctx):
        """Create a Xaman TrustSet payload and return the signing link."""
        issuer = getattr(settings, "SUBSCRIPTION_CURRENCY_ISSUER", "")
        if not issuer:
            ctx["error"] = "Currency issuer is not configured. Contact an admin."
            return render(request, self.template_name, ctx)

        try:
            from blockchain.xrpl.xrpl_tx import encode_currency_hex
            from blockchain.xrpl.xaman import create_trustline_payload

            currency_code = getattr(
                settings, "SUBSCRIPTION_CURRENCY_CODE", "FakeRLUSD"
            )
            hex_code = encode_currency_hex(currency_code)
            payload = create_trustline_payload(hex_code, issuer)

            ctx["trustline_deeplink"] = payload["deeplink"]
            ctx["trustline_currency"] = currency_code
            logger.info(
                f"Faucet: created TrustSet payload for {currency_code} "
                f"(uuid: {payload['uuid']})"
            )
        except Exception as e:
            ctx["error"] = f"Failed to create trust line request: {e}"
            logger.warning(f"Faucet trustline error: {e}")

        return render(request, self.template_name, ctx)

    def _handle_faucet(self, request, ctx):
        """Validate address and send FakeRLUSD."""
        wallet = request.POST.get("wallet_address", "").strip()
        ctx["wallet_address"] = wallet

        if not wallet:
            ctx["error"] = "Please enter a wallet address."
            return render(request, self.template_name, ctx)

        if not _RADDRESS_RE.match(wallet):
            ctx["error"] = (
                "Invalid wallet address. XRPL addresses start with 'r' "
                "and are 25-35 characters long."
            )
            return render(request, self.template_name, ctx)

        faucet_seed = getattr(settings, "FAUCET_WALLET_SEED", "")
        if not faucet_seed:
            ctx["error"] = "Faucet is not configured. Contact an admin."
            return render(request, self.template_name, ctx)

        amount = getattr(settings, "FAUCET_AMOUNT", 20)
        currency = getattr(settings, "SUBSCRIPTION_CURRENCY_CODE", "FakeRLUSD")

        try:
            from blockchain.xrpl.xrpl_tx import send_faucet_payment

            tx_hash = send_faucet_payment(wallet)
            ctx["success"] = True
            ctx["tx_hash"] = tx_hash
            ctx["amount"] = amount
            ctx["currency"] = currency
            logger.info(
                f"Faucet: sent {amount} {currency} to {wallet} (tx: {tx_hash})"
            )
        except Exception as e:
            ctx["error"] = f"Transaction failed: {e}"
            logger.warning(f"Faucet error for {wallet}: {e}")

        return render(request, self.template_name, ctx)
