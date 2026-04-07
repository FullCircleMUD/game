"""
Faucet page — dispense FakeRLUSD for testnet subscription payments.

Only accessible when IS_TESTNET is True. Redirects to home on mainnet.
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
        return render(request, self.template_name)

    def post(self, request):
        if not getattr(settings, "IS_TESTNET", False):
            return redirect("/")

        wallet = request.POST.get("wallet_address", "").strip()
        ctx = {"wallet_address": wallet}

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
