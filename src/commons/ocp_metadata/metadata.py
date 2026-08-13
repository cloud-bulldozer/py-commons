import functools
import logging
import os

logger = logging.getLogger("commons.ocp_metadata")

_NON_OCP_DEFAULTS = {
    "ocpVersion": "",
    "clusterVersion": "",
    "ocpMajorVersion": "",
    "stream": "",
    "platform": "",
    "clusterName": "",
    "clusterType": "self-managed",
    "region": "",
    "sdnType": "",
    "fips": False,
    "publish": "",
    "workerArch": "",
    "controlPlaneArch": "",
    "ipsec": False,
    "ipsecMode": "Disabled",
}


@functools.lru_cache(maxsize=1)
def _get_client():
    from kubernetes import client, config as k8s_config

    if os.environ.get("KUBECONFIG"):
        k8s_config.load_kube_config()
    else:
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()
    return client


def _get_custom_resource(group, version, plural, name):
    api = _get_client().CustomObjectsApi()
    try:
        return api.get_cluster_custom_object(group, version, plural, name)
    except Exception as e:
        logger.debug("Failed to get %s/%s %s: %s", group, plural, name, e)
        return {}


def _get_namespaced_custom_resource(group, version, namespace, plural, name):
    api = _get_client().CustomObjectsApi()
    try:
        return api.get_namespaced_custom_object(group, version, namespace, plural, name)
    except Exception as e:
        logger.debug("Failed to get %s/%s/%s %s: %s", namespace, group, plural, name, e)
        return {}


def _list_nodes(label_selector=""):
    v1 = _get_client().CoreV1Api()
    try:
        return v1.list_node(label_selector=label_selector).items
    except Exception as e:
        logger.debug("Failed to list nodes (selector=%s): %s", label_selector, e)
        return []


def _get_configmap(namespace, name):
    v1 = _get_client().CoreV1Api()
    try:
        return v1.read_namespaced_config_map(name, namespace)
    except Exception as e:
        logger.debug("Failed to get configmap %s/%s: %s", namespace, name, e)
        return None


def _detect_distribution():
    cm = _get_configmap("kube-public", "microshift-version")
    if cm is not None:
        version = cm.data.get("version", "") if cm.data else ""
        return "microshift", version

    try:
        api_groups = [g.name for g in _get_client().ApisApi().get_api_versions().groups]
    except Exception:
        api_groups = []

    if "config.openshift.io" in api_groups:
        return "openshift", ""
    if "route.openshift.io" in api_groups:
        return "microshift", ""
    return "kubernetes", ""


def _detect_cluster_type(infra):
    status = infra.get("status", {})
    platform = status.get("platform", "")
    if not platform:
        return "self-managed"

    topology = status.get("controlPlaneTopology", "")
    is_hcp = topology == "External"

    platform_key = {"AWS": "aws", "Azure": "azure"}.get(platform)
    if not platform_key:
        return "self-managed"

    tags = status.get("platformStatus", {}).get(platform_key, {}).get("resourceTags", [])
    for tag in tags:
        if isinstance(tag, dict) and tag.get("key") == "red-hat-clustertype":
            val = tag.get("value", "")
            if val in ("rosa", "aro"):
                return f"{val}-hcp" if is_hcp else val
            return val

    return "self-managed"


def _get_region(infra):
    status = infra.get("status", {})
    platform = status.get("platform", "")
    ps = status.get("platformStatus", {})
    platform_key = {"AWS": "aws", "Azure": "azure"}.get(platform)
    if platform_key:
        return ps.get(platform_key, {}).get("region", "")
    return ""


def _get_install_config():
    cm = _get_configmap("kube-system", "cluster-config-v1")
    if not cm or not cm.data or "install-config" not in cm.data:
        return None
    try:
        import yaml
        return yaml.safe_load(cm.data["install-config"])
    except Exception as e:
        logger.debug("Failed to parse install-config: %s", e)
        return None


def _extract_install_fields(config):
    if not config:
        return {"fips": False, "publish": "", "workerArch": "", "controlPlaneArch": ""}

    worker_arch = ""
    for pool in config.get("compute", []):
        if pool.get("name") == "worker":
            worker_arch = pool.get("architecture", "")
            break

    return {
        "fips": bool(config.get("fips", False)),
        "publish": config.get("publish", ""),
        "workerArch": worker_arch,
        "controlPlaneArch": config.get("controlPlane", {}).get("architecture", ""),
    }


def _get_k8s_version():
    try:
        version = _get_client().VersionApi().get_code()
        return version.git_version
    except Exception as e:
        logger.debug("Failed to get k8s version: %s", e)
        return ""


def _get_ipsec():
    network = _get_custom_resource(
        "operator.openshift.io", "v1", "networks", "cluster"
    )
    if not network:
        return False, "Disabled"
    ovn = network.get("spec", {}).get("defaultNetwork", {}).get("ovnKubernetesConfig", {})
    ipsec_config = ovn.get("ipsecConfig")
    if ipsec_config is None:
        return False, "Disabled"
    mode = ipsec_config.get("mode", "")
    if not mode:
        return True, "Full"
    if mode != "Disabled":
        return True, mode
    return False, "Disabled"


def _get_nodes_info(infra):
    all_nodes = _list_nodes()

    metadata = {
        "masterNodesCount": 0,
        "workerNodesCount": 0,
        "infraNodesCount": 0,
        "otherNodesCount": 0,
        "totalNodes": len(all_nodes),
        "masterNodesType": "",
        "workerNodesType": "",
        "infraNodesType": "",
        "totalWorkerCPU": 0,
        "totalWorkerMemoryKi": 0,
    }

    for node in all_nodes:
        labels = node.metadata.labels or {}
        instance_type = labels.get("node.kubernetes.io/instance-type", "")
        taints = node.spec.taints or []
        capacity = node.status.capacity or {}

        is_master = "node-role.kubernetes.io/master" in labels
        is_control_plane = "node-role.kubernetes.io/control-plane" in labels
        is_infra = "node-role.kubernetes.io/infra" in labels
        is_worker = "node-role.kubernetes.io/worker" in labels

        def _count_as_worker():
            metadata["workerNodesCount"] += 1
            if not metadata["workerNodesType"]:
                metadata["workerNodesType"] = instance_type
            cpu = capacity.get("cpu", "0")
            mem = capacity.get("memory", "0Ki").replace("Ki", "")
            metadata["totalWorkerCPU"] += int(cpu)
            try:
                metadata["totalWorkerMemoryKi"] += int(mem)
            except ValueError:
                pass

        if is_master or is_control_plane:
            metadata["masterNodesCount"] += 1
            if not metadata["masterNodesType"]:
                metadata["masterNodesType"] = instance_type
            if is_master and is_worker and len(taints) == 0:
                _count_as_worker()
        elif is_infra:
            metadata["infraNodesCount"] += 1
            if not metadata["infraNodesType"]:
                metadata["infraNodesType"] = instance_type
        elif is_worker:
            _count_as_worker()
        else:
            metadata["otherNodesCount"] += 1

    if infra:
        topology = infra.get("status", {}).get("controlPlaneTopology", "")
        if topology == "External":
            metadata["masterNodesCount"] = 0
            metadata["masterNodesType"] = ""

    return metadata


def get_cluster_metadata():
    """Collect OCP cluster metadata."""
    metadata = {}

    distribution, ms_version = _detect_distribution()
    metadata["distribution"] = distribution

    if distribution == "microshift":
        metadata["microshift"] = True
        metadata["microshiftVersion"] = ms_version
        if ms_version:
            parts = ms_version.split(".")
            metadata["microshiftMajorVersion"] = (
                ".".join(parts[:2]) if len(parts) >= 2 else ms_version
            )
    else:
        metadata["microshift"] = False

    metadata["k8sVersion"] = _get_k8s_version()

    if distribution != "openshift":
        metadata.update(_NON_OCP_DEFAULTS)
        metadata.update(_get_nodes_info(None))
        logger.warning(
            "Could not collect OCP metadata — "
            "kubernetes client may not be configured or cluster not accessible"
        )
        return metadata

    cv = _get_custom_resource(
        "config.openshift.io", "v1", "clusterversions", "version"
    )
    ocp_version = ""
    if cv:
        for entry in cv.get("status", {}).get("history", []):
            if entry.get("state") == "Completed":
                ocp_version = entry.get("version", "")
                break
    metadata["ocpVersion"] = ocp_version
    metadata["clusterVersion"] = ocp_version
    if ocp_version:
        parts = ocp_version.split(".")
        metadata["ocpMajorVersion"] = (
            ".".join(parts[:2]) if len(parts) >= 2 else ocp_version
        )
        metadata["stream"] = "okd" if ".okd-" in ocp_version.lower() else "ocp"
    else:
        metadata["ocpMajorVersion"] = ""
        metadata["stream"] = ""

    infra = _get_custom_resource(
        "config.openshift.io", "v1", "infrastructures", "cluster"
    )
    infra_status = infra.get("status", {}) if infra else {}
    metadata["platform"] = infra_status.get("platform", "")
    metadata["clusterName"] = infra_status.get("infrastructureName", "")
    metadata["clusterType"] = _detect_cluster_type(infra) if infra else "self-managed"
    metadata["region"] = _get_region(infra) if infra else ""

    network = _get_custom_resource(
        "config.openshift.io", "v1", "networks", "cluster"
    )
    metadata["sdnType"] = (
        network.get("status", {}).get("networkType", "") if network else ""
    )

    metadata.update(_get_nodes_info(infra))
    metadata.update(_extract_install_fields(_get_install_config()))

    ipsec, ipsec_mode = _get_ipsec()
    metadata["ipsec"] = ipsec
    metadata["ipsecMode"] = ipsec_mode

    if metadata["clusterVersion"]:
        logger.info(
            "Collected metadata: cluster=%s platform=%s type=%s workers=%d region=%s",
            metadata["clusterVersion"],
            metadata["platform"],
            metadata["clusterType"],
            metadata["workerNodesCount"],
            metadata["region"],
        )
    else:
        logger.warning(
            "Could not collect OCP metadata — "
            "kubernetes client may not be configured or cluster not accessible"
        )

    return metadata


def get_prometheus(sa_name="prometheus-k8s", namespace="openshift-monitoring"):
    """Discover Prometheus endpoint and bearer token.

    Uses thanos-querier when PROMETHEUS_BACKEND=thanos.
    Uses prometheus-k8s by default.

    Returns (prometheus_url, bearer_token).
    """
    backend = os.environ.get("PROMETHEUS_BACKEND", "prometheus").lower()
    route_name = "thanos-querier" if backend == "thanos" else "prometheus-k8s"

    route = _get_namespaced_custom_resource(
        "route.openshift.io", "v1", namespace, "routes", route_name
    )
    if not route:
        logger.warning("Could not discover %s route", route_name)
        return "", ""

    host = route.get("spec", {}).get("host", "")
    if not host:
        logger.warning("%s route has no host", route_name)
        return "", ""
    prometheus_url = f"https://{host}"

    client = _get_client()
    v1 = client.CoreV1Api()
    try:
        token_request = client.AuthenticationV1TokenRequest(
            spec=client.V1TokenRequestSpec(
                expiration_seconds=36000,
            )
        )
        response = v1.create_namespaced_service_account_token(
            sa_name, namespace, token_request
        )
        token = response.status.token
    except Exception as e:
        logger.warning("Could not obtain bearer token for Prometheus: %s", e)
        return prometheus_url, ""

    logger.info("%s discovered: %s", route_name, prometheus_url)
    return prometheus_url, token
