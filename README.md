# py-commons

A collection of shared Python libraries for Red Hat tools and automation.

## Libraries

### commons.indexers

Multi-backend metrics indexer supporting Elasticsearch, OpenSearch, and local JSON file backends.

**Features:**
- Factory pattern for backend selection (`new_indexer(config)`)
- Elasticsearch and OpenSearch backends with SHA-256 document deduplication
- Local JSON file backend with append support
- Configurable TLS verification
- Consistent interface across all backends

See [indexers documentation](src/commons/indexers/README.md) for detailed usage.

### commons.ocp_metadata

OpenShift cluster metadata collector with Prometheus/Thanos endpoint discovery.

**Features:**
- Comprehensive cluster metadata (version, platform, region, node counts, instance types)
- Cluster type detection (self-managed, ROSA, ARO, HCP)
- Distribution detection (OpenShift, MicroShift, Kubernetes)
- Network configuration (SDN type, IPSec)
- Install config fields (FIPS, architecture, publish strategy)
- Prometheus/Thanos endpoint and bearer token discovery

See [ocp_metadata documentation](src/commons/ocp_metadata/README.md) for detailed usage.

### commons.jira

A unified JIRA client for Red Hat projects with support for both Atlassian Cloud and on-premise instances.

**Features:**
- Unified authentication for Cloud (email + API token) and on-premise (username/password or token)
- Automatic retry logic with exponential backoff
- Common query patterns (by status, label, custom JQL)
- Issue management (create, update, transition, labels, comments)
- Custom field support
- Comprehensive error handling

See [jira documentation](src/commons/jira/README.md) for detailed usage.

### commons.release

Query OpenShift release-controller for payload phase (`Accepted` / `Rejected` / `Pending`). See [release documentation](src/commons/release/README.md).

## Installation

Install from PyPI:

```bash
pip install py-commons
```

Or install from source:

```bash
git clone https://github.com/redhat-performance/py-commons.git
cd py-commons
pip install -e .
```

## Usage

### Indexers

```python
from commons.indexers import IndexerConfig, new_indexer

# Elasticsearch
config = IndexerConfig(type="elastic", servers=["http://es:9200"], index="perf-results")
indexer = new_indexer(config)
indexer.index([{"uuid": "abc", "metricName": "latency", "p99": 42.5}])

# OpenSearch
config = IndexerConfig(type="opensearch", servers=["https://os:9200"], index="perf-results")
indexer = new_indexer(config)
indexer.index([{"uuid": "abc", "metricName": "latency", "p99": 42.5}])

# Local JSON files
config = IndexerConfig(type="local", metrics_directory="/tmp/results")
indexer = new_indexer(config)
indexer.index([{"uuid": "abc", "value": 42}], metric_name="latency")
```

### OCP Metadata

```python
from commons.ocp_metadata import get_cluster_metadata, get_prometheus

# Collect cluster metadata (requires kubernetes package and cluster access)
metadata = get_cluster_metadata()
print(metadata["clusterVersion"])   # "4.17.3"
print(metadata["platform"])         # "AWS"
print(metadata["workerNodesCount"]) # 3
print(metadata["region"])           # "us-east-1"

# Discover Prometheus endpoint
url, token = get_prometheus()
print(url)    # "https://thanos-querier-openshift-monitoring.apps.cluster.example.com"
```

### JIRA

```python
from commons.jira import JiraClient

# Connect to Atlassian Cloud
client = JiraClient(
    server="https://yourcompany.atlassian.net",
    email="you@example.com",
    api_token="your-api-token"
)

# Query issues
issues = client.query_issues("project = MYPROJECT AND status = 'In Progress'")

# Get issues by status
bugs = client.get_issues_by_status("MYPROJECT", "Open")

# Add label to issue
client.add_label(issues[0], "needs-review")
```

```python
from commons.release import ReleaseControllerClient

phase = ReleaseControllerClient().get_payload_phase(
    "4.22.0-0.nightly-2026-01-05-203335",
    "4.22",
)
```

## License

See [LICENSE](LICENSE) for details.
