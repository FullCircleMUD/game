"""
Tests for the Xaman API wrapper.

evennia test --settings settings tests.server_tests.test_xaman
"""

from unittest import TestCase
from unittest.mock import patch, MagicMock


class TestCreateSigninPayload(TestCase):
    """Test create_signin_payload()."""

    @patch("blockchain.xrpl.xaman.requests.post")
    def test_success(self, mock_post):
        """Should return uuid, deeplink, qr_url."""
        from blockchain.xrpl.xaman import create_signin_payload

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "uuid": "test-uuid-123",
                "next": {"always": "https://xaman.app/sign/test-uuid-123"},
                "refs": {"qr_png": "https://xaman.app/sign/test-uuid-123.png"},
            },
        )

        result = create_signin_payload()
        self.assertEqual(result["uuid"], "test-uuid-123")
        self.assertIn("xaman.app", result["deeplink"])
        self.assertIn(".png", result["qr_url"])

    @patch("blockchain.xrpl.xaman.requests.post")
    def test_api_error(self, mock_post):
        """Should raise XamanAPIError on non-200."""
        from blockchain.xrpl.xaman import create_signin_payload, XamanAPIError

        mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")

        with self.assertRaises(XamanAPIError):
            create_signin_payload()


class TestGetPayloadStatus(TestCase):
    """Test get_payload_status()."""

    @patch("blockchain.xrpl.xaman.requests.get")
    def test_pending(self, mock_get):
        """Should return resolved=False when not yet signed."""
        from blockchain.xrpl.xaman import get_payload_status

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "meta": {"resolved": False, "signed": False, "expired": False},
                "response": {},
            },
        )

        result = get_payload_status("test-uuid")
        self.assertFalse(result["resolved"])
        self.assertFalse(result["signed"])
        self.assertIsNone(result["wallet_address"])

    @patch("blockchain.xrpl.xaman.requests.get")
    def test_signed(self, mock_get):
        """Should return wallet_address when signed."""
        from blockchain.xrpl.xaman import get_payload_status

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "meta": {"resolved": True, "signed": True, "expired": False},
                "response": {"account": "rNiceWalletAddress123"},
            },
        )

        result = get_payload_status("test-uuid")
        self.assertTrue(result["resolved"])
        self.assertTrue(result["signed"])
        self.assertEqual(result["wallet_address"], "rNiceWalletAddress123")

    @patch("blockchain.xrpl.xaman.requests.get")
    def test_rejected(self, mock_get):
        """Should return signed=False when user rejected."""
        from blockchain.xrpl.xaman import get_payload_status

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "meta": {"resolved": True, "signed": False, "expired": False},
                "response": {},
            },
        )

        result = get_payload_status("test-uuid")
        self.assertTrue(result["resolved"])
        self.assertFalse(result["signed"])

    @patch("blockchain.xrpl.xaman.requests.get")
    def test_expired(self, mock_get):
        """Should return expired=True when payload expired."""
        from blockchain.xrpl.xaman import get_payload_status

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "meta": {"resolved": False, "signed": False, "expired": True},
                "response": {},
            },
        )

        result = get_payload_status("test-uuid")
        self.assertTrue(result["expired"])

    @patch("blockchain.xrpl.xaman.requests.get")
    def test_api_error(self, mock_get):
        """Should raise XamanAPIError on non-200."""
        from blockchain.xrpl.xaman import get_payload_status, XamanAPIError

        mock_get.return_value = MagicMock(status_code=500, text="Server error")

        with self.assertRaises(XamanAPIError):
            get_payload_status("test-uuid")
