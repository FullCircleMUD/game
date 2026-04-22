"""Tests for blockchain.xrpl.cosigner_ping — keep-alive pinger.

Covers:
  - no-op when XRPL_MULTISIG_ENABLED is False
  - no-op when XRPL_COSIGNER_URL is empty
  - httpx exceptions are swallowed (best-effort)
  - happy path hits /health on the configured URL
"""

from unittest import TestCase
from unittest.mock import patch, MagicMock

from django.test import override_settings

from blockchain.xrpl import cosigner_ping


class CosignerPingTests(TestCase):
    """Direct tests of _blocking_ping — skips the deferToThread wrapper."""

    @override_settings(XRPL_MULTISIG_ENABLED=False, XRPL_COSIGNER_URL="https://x.example")
    @patch("blockchain.xrpl.cosigner_ping.httpx")
    def test_noop_when_multisig_disabled(self, mock_httpx):
        cosigner_ping._blocking_ping()
        mock_httpx.get.assert_not_called()

    @override_settings(XRPL_MULTISIG_ENABLED=True, XRPL_COSIGNER_URL="")
    @patch("blockchain.xrpl.cosigner_ping.httpx")
    def test_noop_when_url_empty(self, mock_httpx):
        cosigner_ping._blocking_ping()
        mock_httpx.get.assert_not_called()

    @override_settings(XRPL_MULTISIG_ENABLED=True, XRPL_COSIGNER_URL="https://x.example")
    @patch("blockchain.xrpl.cosigner_ping.httpx")
    def test_swallows_exception(self, mock_httpx):
        mock_httpx.get.side_effect = RuntimeError("network down")
        # Should not raise.
        cosigner_ping._blocking_ping()
        mock_httpx.get.assert_called_once()

    @override_settings(XRPL_MULTISIG_ENABLED=True, XRPL_COSIGNER_URL="https://x.example/")
    @patch("blockchain.xrpl.cosigner_ping.httpx")
    def test_happy_path_hits_health(self, mock_httpx):
        mock_resp = MagicMock(status_code=200)
        mock_httpx.get.return_value = mock_resp
        cosigner_ping._blocking_ping()
        # Trailing slash on configured URL is stripped; /health is appended.
        mock_httpx.get.assert_called_once_with(
            "https://x.example/health", timeout=30.0
        )
