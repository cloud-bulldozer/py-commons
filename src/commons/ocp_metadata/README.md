# commons.ocp_metadata

OpenShift cluster metadata collector with Prometheus/Thanos endpoint discovery.

Requires the `kubernetes` Python package and cluster access (via `$KUBECONFIG` or in-cluster ServiceAccount token).

## Usage

```python
from commons.ocp_metadata import get_cluster_metadata, get_prometheus

# Collect all cluster metadata
metadata = get_cluster_metadata()

# Use specific fields
print(metadata["clusterVersion"])    # "4.17.3"
print(metadata["platform"])          # "AWS"
print(metadata["region"])            # "us-east-1"
print(metadata["clusterType"])       # "self-managed" / "rosa" / "aro"
print(metadata["workerNodesCount"])  # 3
print(metadata["workerNodesType"])   # "m5.2xlarge"
print(metadata["totalWorkerCPU"])    # 96

# Discover Prometheus endpoint
url, token = get_prometheus()
# url:   "https://thanos-querier-openshift-monitoring.apps.cluster.example.com"
# token: bearer token valid for 10 hours
```

## Metadata Fields

### Cluster Identity

| Field | Description |
|---|---|
| `clusterVersion` | OCP version (e.g. `"4.17.3"`) |
| `ocpVersion` | Same as clusterVersion |
| `ocpMajorVersion` | Major.minor (e.g. `"4.17"`) |
| `k8sVersion` | Kubernetes version |
| `platform` | Infrastructure platform (AWS, Azure, GCP, etc.) |
| `clusterName` | Infrastructure name |
| `clusterType` | `"self-managed"`, `"rosa"`, `"rosa-hcp"`, `"aro"`, `"aro-hcp"` |
| `region` | Cloud region (e.g. `"us-east-1"`) |
| `distribution` | `"openshift"`, `"microshift"`, or `"kubernetes"` |
| `stream` | `"ocp"` or `"okd"` |

### Node Counts

| Field | Description |
|---|---|
| `masterNodesCount` | Master/control-plane node count |
| `workerNodesCount` | Worker node count |
| `infraNodesCount` | Infra node count |
| `totalNodes` | Total node count |
| `otherNodesCount` | Nodes without a recognized role |

### Node Types

| Field | Description |
|---|---|
| `masterNodesType` | Master instance type (e.g. `"m5.xlarge"`) |
| `workerNodesType` | Worker instance type |
| `infraNodesType` | Infra instance type |

### Resources

| Field | Description |
|---|---|
| `totalWorkerCPU` | Total CPU cores across all workers |
| `totalWorkerMemoryKi` | Total memory (KiB) across all workers |

### Configuration

| Field | Description |
|---|---|
| `sdnType` | Network type (e.g. `"OVNKubernetes"`) |
| `fips` | FIPS mode (`"true"` / `"false"`) |
| `publish` | Publish strategy |
| `workerArch` | Worker architecture (e.g. `"amd64"`) |
| `controlPlaneArch` | Control plane architecture |
| `ipsec` | IPSec enabled (bool) |
| `ipsecMode` | IPSec mode or `"Disabled"` |

### MicroShift

| Field | Description |
|---|---|
| `microshift` | Is MicroShift (bool) |
| `microshiftVersion` | MicroShift version |
| `microshiftMajorVersion` | Major.minor version |

## get_prometheus()

Discovers the Thanos querier route and obtains a bearer token.

```python
url, token = get_prometheus(
    sa_name="prometheus-k8s",           # ServiceAccount name
    namespace="openshift-monitoring",   # SA namespace
)
```

Token is valid for 10 hours.
