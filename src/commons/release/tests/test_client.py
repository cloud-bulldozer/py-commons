"""Tests for commons.release client."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from commons.release import RELEASE_CONTROLLER_API, ReleaseControllerClient


class TestReleaseControllerClient(unittest.IsolatedAsyncioTestCase):

    def test_url(self):
        client = ReleaseControllerClient()
        self.assertEqual(
            client._url("4.22.0-0.nightly-2026-01-05-203335", "4.22"),
            f"{RELEASE_CONTROLLER_API}/releasestream/4.22.0-0.nightly/"
            "release/4.22.0-0.nightly-2026-01-05-203335",
        )

    def test_parse_phase(self):
        client = ReleaseControllerClient()
        self.assertEqual(client._parse_phase({"phase": "Rejected"}), "Rejected")
        self.assertIsNone(client._parse_phase(["Rejected"]))
        self.assertIsNone(client._parse_phase({"phase": 1}))

    async def test_async_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"phase": "Accepted"}
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("commons.release.client.httpx.AsyncClient", return_value=mock_client):
            phase = await ReleaseControllerClient().get_payload_phase(
                "4.22.0-0.nightly-2026-01-05-203335", "4.22"
            )
        self.assertEqual(phase, "Accepted")

    async def test_async_error_returns_none(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("boom")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("commons.release.client.httpx.AsyncClient", return_value=mock_client):
            phase = await ReleaseControllerClient().get_payload_phase(
                "4.22.0-0.nightly-2026-01-05-203335", "4.22"
            )
        self.assertIsNone(phase)

    def test_sync_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"phase": "Pending"}
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        with patch("commons.release.client.httpx.Client", return_value=mock_client):
            phase = ReleaseControllerClient().get_payload_phase_sync(
                "4.22.0-0.nightly-2026-01-05-203335", "4.22"
            )
        self.assertEqual(phase, "Pending")


if __name__ == "__main__":
    unittest.main()
