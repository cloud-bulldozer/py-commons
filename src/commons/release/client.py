"""OpenShift release-controller client for payload phase checks."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RELEASE_CONTROLLER_API = "https://amd64.ocp.releases.ci.openshift.org/api/v1"
RELEASE_CONTROLLER_TIMEOUT = 10.0


class ReleaseControllerClient:  # pylint: disable=too-few-public-methods
    """Query payload acceptance phase from the release-controller API."""

    def __init__(
        self,
        base_url: str = RELEASE_CONTROLLER_API,
        timeout: float = RELEASE_CONTROLLER_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, nightly_version: str, major_version: str) -> str:
        stream = f"{major_version}.0-0.nightly"
        return f"{self.base_url}/releasestream/{stream}/release/{nightly_version}"

    def _parse_phase(self, payload: object) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        phase = payload.get("phase")
        return phase if isinstance(phase, str) else None

    def get_payload_phase(
        self, nightly_version: str, major_version: str
    ) -> Optional[str]:
        """Return phase string, or None on error (fail-open)."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(self._url(nightly_version, major_version))
                resp.raise_for_status()
                return self._parse_phase(resp.json())
        except (httpx.HTTPError, ValueError, TypeError):
            logger.debug(
                "release-controller query failed for %s",
                nightly_version,
                exc_info=True,
            )
            return None
