"""
commons.ocp_metadata - OpenShift Cluster Metadata Collector

Collects comprehensive OCP cluster metadata including node counts,
instance types, platform details, and cluster configuration.
Includes Prometheus/Thanos endpoint discovery.

Requires: pip install rh-py-commons[ocp_metadata]
"""

try:
    from .metadata import get_cluster_metadata, get_prometheus
except ImportError as exc:
    raise ImportError(
        "ocp_metadata requires extra dependencies. "
        "Install with: pip install 'rh-py-commons[ocp_metadata]'"
    ) from exc

__all__ = ["get_cluster_metadata", "get_prometheus"]
