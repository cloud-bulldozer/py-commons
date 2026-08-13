"""
commons.ocp_metadata - OpenShift Cluster Metadata Collector

Collects comprehensive OCP cluster metadata including node counts,
instance types, platform details, and cluster configuration.
Includes Prometheus/Thanos endpoint discovery.
"""

from .metadata import get_cluster_metadata, get_prometheus

__all__ = ["get_cluster_metadata", "get_prometheus"]
