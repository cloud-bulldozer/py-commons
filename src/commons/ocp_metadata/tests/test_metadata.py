"""Tests for ocp_metadata module."""

import unittest
from unittest.mock import MagicMock, patch

from commons.ocp_metadata.metadata import (
    _detect_cluster_type,
    _extract_install_fields,
    _get_region,
    get_cluster_metadata,
    get_prometheus,
)


class TestDetectClusterType(unittest.TestCase):
    """Test cluster type detection from infrastructure resource."""

    def test_self_managed_no_platform(self):
        """Test self-managed when no platform is set."""
        infra = {"status": {}}
        self.assertEqual(_detect_cluster_type(infra), "self-managed")

    def test_self_managed_unsupported_platform(self):
        """Test self-managed for non-AWS/Azure platform."""
        infra = {"status": {"platform": "GCP"}}
        self.assertEqual(_detect_cluster_type(infra), "self-managed")

    def test_rosa_from_resource_tags(self):
        """Test ROSA detection from AWS resource tags."""
        infra = {
            "status": {
                "platform": "AWS",
                "controlPlaneTopology": "HighlyAvailable",
                "platformStatus": {
                    "aws": {
                        "resourceTags": [
                            {"key": "red-hat-clustertype", "value": "rosa"}
                        ]
                    }
                },
            }
        }
        self.assertEqual(_detect_cluster_type(infra), "rosa")

    def test_rosa_hcp(self):
        """Test ROSA HCP detection with External topology."""
        infra = {
            "status": {
                "platform": "AWS",
                "controlPlaneTopology": "External",
                "platformStatus": {
                    "aws": {
                        "resourceTags": [
                            {"key": "red-hat-clustertype", "value": "rosa"}
                        ]
                    }
                },
            }
        }
        self.assertEqual(_detect_cluster_type(infra), "rosa-hcp")

    def test_aro_from_tags(self):
        """Test ARO detection from Azure resource tags."""
        infra = {
            "status": {
                "platform": "Azure",
                "controlPlaneTopology": "HighlyAvailable",
                "platformStatus": {
                    "azure": {
                        "resourceTags": [
                            {"key": "red-hat-clustertype", "value": "aro"}
                        ]
                    }
                },
            }
        }
        self.assertEqual(_detect_cluster_type(infra), "aro")

    def test_self_managed_no_tags(self):
        """Test self-managed when AWS has no resource tags."""
        infra = {
            "status": {
                "platform": "AWS",
                "platformStatus": {"aws": {}},
            }
        }
        self.assertEqual(_detect_cluster_type(infra), "self-managed")


class TestGetRegion(unittest.TestCase):
    """Test region extraction from infrastructure resource."""

    def test_aws_region(self):
        """Test AWS region extraction."""
        infra = {
            "status": {
                "platform": "AWS",
                "platformStatus": {"aws": {"region": "us-east-1"}},
            }
        }
        self.assertEqual(_get_region(infra), "us-east-1")

    def test_azure_region(self):
        """Test Azure region extraction."""
        infra = {
            "status": {
                "platform": "Azure",
                "platformStatus": {"azure": {"region": "eastus"}},
            }
        }
        self.assertEqual(_get_region(infra), "eastus")

    def test_no_region_unsupported_platform(self):
        """Test empty region for unsupported platform."""
        infra = {"status": {"platform": "GCP", "platformStatus": {}}}
        self.assertEqual(_get_region(infra), "")


class TestExtractInstallFields(unittest.TestCase):
    """Test install-config field extraction."""

    def test_none_config_returns_defaults(self):
        """Test default values when config is None."""
        result = _extract_install_fields(None)
        self.assertFalse(result["fips"])
        self.assertEqual(result["publish"], "")
        self.assertEqual(result["workerArch"], "")

    def test_extracts_fips_and_publish(self):
        """Test fips and publish extraction."""
        config = {"fips": True, "publish": "Internal"}
        result = _extract_install_fields(config)
        self.assertTrue(result["fips"])
        self.assertEqual(result["publish"], "Internal")

    def test_extracts_worker_arch(self):
        """Test worker architecture extraction from compute pools."""
        config = {
            "compute": [
                {"name": "worker", "architecture": "amd64"},
                {"name": "infra", "architecture": "arm64"},
            ]
        }
        result = _extract_install_fields(config)
        self.assertEqual(result["workerArch"], "amd64")

    def test_extracts_control_plane_arch(self):
        """Test control plane architecture extraction."""
        config = {"controlPlane": {"architecture": "arm64"}}
        result = _extract_install_fields(config)
        self.assertEqual(result["controlPlaneArch"], "arm64")


class TestGetClusterMetadata(unittest.TestCase):
    """Test get_cluster_metadata with mocked Kubernetes API."""

    @patch("commons.ocp_metadata.metadata._get_ipsec", return_value=(False, "Disabled"))
    @patch("commons.ocp_metadata.metadata._get_install_config", return_value=None)
    @patch("commons.ocp_metadata.metadata._get_nodes_info")
    @patch("commons.ocp_metadata.metadata._get_custom_resource")
    @patch("commons.ocp_metadata.metadata._get_k8s_version", return_value="v1.28.6")
    @patch("commons.ocp_metadata.metadata._detect_distribution", return_value=("openshift", ""))
    def test_openshift_cluster(
        self, mock_dist, mock_k8s_ver, mock_cr, mock_nodes, mock_ic, mock_ipsec
    ):
        """Test metadata collection for an OpenShift cluster."""
        mock_cr.side_effect = [
            {"status": {"history": [{"state": "Completed", "version": "4.16.3"}]}},
            {"status": {"platform": "AWS", "infrastructureName": "test-cluster",
                        "platformStatus": {"aws": {"region": "us-east-1"}}}},
            {"status": {"networkType": "OVNKubernetes"}},
        ]
        mock_nodes.return_value = {
            "masterNodesCount": 3,
            "workerNodesCount": 3,
            "infraNodesCount": 0,
            "otherNodesCount": 0,
            "totalNodes": 6,
            "masterNodesType": "m5.xlarge",
            "workerNodesType": "m5.2xlarge",
            "infraNodesType": "",
            "totalWorkerCPU": 24,
            "totalWorkerMemoryKi": 98304,
        }

        # Clear the lru_cache so mocks work
        from commons.ocp_metadata.metadata import _get_client
        _get_client.cache_clear()

        result = get_cluster_metadata()

        self.assertEqual(result["distribution"], "openshift")
        self.assertEqual(result["ocpVersion"], "4.16.3")
        self.assertEqual(result["clusterVersion"], "4.16.3")
        self.assertEqual(result["ocpMajorVersion"], "4.16")
        self.assertEqual(result["platform"], "AWS")
        self.assertEqual(result["clusterName"], "test-cluster")
        self.assertEqual(result["sdnType"], "OVNKubernetes")
        self.assertEqual(result["k8sVersion"], "v1.28.6")
        self.assertEqual(result["workerNodesCount"], 3)
        self.assertEqual(result["stream"], "ocp")

    @patch("commons.ocp_metadata.metadata._get_nodes_info")
    @patch("commons.ocp_metadata.metadata._get_k8s_version", return_value="v1.28.0")
    @patch("commons.ocp_metadata.metadata._detect_distribution", return_value=("kubernetes", ""))
    def test_non_ocp_cluster(self, mock_dist, mock_k8s_ver, mock_nodes):
        """Test metadata collection for a non-OCP cluster returns defaults."""
        mock_nodes.return_value = {
            "masterNodesCount": 1,
            "workerNodesCount": 2,
            "infraNodesCount": 0,
            "otherNodesCount": 0,
            "totalNodes": 3,
            "masterNodesType": "",
            "workerNodesType": "",
            "infraNodesType": "",
            "totalWorkerCPU": 8,
            "totalWorkerMemoryKi": 16384,
        }

        result = get_cluster_metadata()

        self.assertEqual(result["distribution"], "kubernetes")
        self.assertEqual(result["ocpVersion"], "")
        self.assertEqual(result["platform"], "")
        self.assertEqual(result["clusterType"], "self-managed")
        self.assertEqual(result["workerNodesCount"], 2)


class TestGetPrometheus(unittest.TestCase):
    """Test Prometheus endpoint discovery."""

    @patch("commons.ocp_metadata.metadata._get_client")
    @patch("commons.ocp_metadata.metadata._get_namespaced_custom_resource")
    def test_prometheus_discovery(self, mock_cr, mock_client):
        """Test Prometheus URL and token discovery."""
        mock_cr.return_value = {
            "spec": {"host": "prometheus-k8s.apps.test.example.com"}
        }

        mock_k8s = MagicMock()
        mock_response = MagicMock()
        mock_response.status.token = "test-token"
        mock_k8s.CoreV1Api.return_value.create_namespaced_service_account_token.return_value = mock_response
        mock_client.return_value = mock_k8s

        url, token = get_prometheus()

        self.assertEqual(url, "https://prometheus-k8s.apps.test.example.com")
        self.assertEqual(token, "test-token")

    @patch("commons.ocp_metadata.metadata._get_namespaced_custom_resource")
    def test_prometheus_route_not_found(self, mock_cr):
        """Test empty result when Prometheus route is not found."""
        mock_cr.return_value = {}
        url, token = get_prometheus()
        self.assertEqual(url, "")
        self.assertEqual(token, "")

    @patch.dict("os.environ", {"PROMETHEUS_BACKEND": "thanos"})
    @patch("commons.ocp_metadata.metadata._get_namespaced_custom_resource")
    def test_thanos_backend(self, mock_cr):
        """Test that thanos backend queries thanos-querier route."""
        mock_cr.return_value = {}
        get_prometheus()
        mock_cr.assert_called_with(
            "route.openshift.io", "v1", "openshift-monitoring",
            "routes", "thanos-querier"
        )


if __name__ == "__main__":
    unittest.main()
