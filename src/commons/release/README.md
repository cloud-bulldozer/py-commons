# commons.release

Query OpenShift release-controller for payload phase (`Accepted` / `Rejected` / `Pending`).

```python
from commons.release import ReleaseControllerClient

client = ReleaseControllerClient()
phase = client.get_payload_phase(
    "4.22.0-0.nightly-2026-01-05-203335",
    "4.22",
)
```

Returns `None` on HTTP/parse errors (fail-open).
