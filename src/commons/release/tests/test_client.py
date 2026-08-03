"""Tests for commons.release client."""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

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

    def _mock_httpx_client(self, *, json_value=None, side_effect=None):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        if json_value is not None:
            mock_resp.json.return_value = json_value
        mock_client = MagicMock()
        if side_effect is not None:
            mock_client.get.side_effect = side_effect
        else:
            mock_client.get.return_value = mock_resp
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        return mock_client

    def test_success(self):
        mock_client = self._mock_httpx_client(json_value={"phase": "Pending"})
        with patch("commons.release.client.httpx.Client", return_value=mock_client):
            phase = ReleaseControllerClient().get_payload_phase(
                "4.22.0-0.nightly-2026-01-05-203335", "4.22"
            )
        self.assertEqual(phase, "Pending")

    def test_error_returns_none(self):
        mock_client = self._mock_httpx_client(side_effect=httpx.ConnectError("boom"))
        with patch("commons.release.client.httpx.Client", return_value=mock_client):
            phase = ReleaseControllerClient().get_payload_phase(
                "4.22.0-0.nightly-2026-01-05-203335", "4.22"
            )
        self.assertIsNone(phase)

    async def test_async_caller_via_to_thread(self):
        mock_client = self._mock_httpx_client(json_value={"phase": "Accepted"})
        with patch("commons.release.client.httpx.Client", return_value=mock_client):
            phase = await asyncio.to_thread(
                ReleaseControllerClient().get_payload_phase,
                "4.22.0-0.nightly-2026-01-05-203335",
                "4.22",
            )
        self.assertEqual(phase, "Accepted")


if __name__ == "__main__":
    unittest.main()
