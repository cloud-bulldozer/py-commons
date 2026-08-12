# commons.indexers

Multi-backend metrics indexer supporting Elasticsearch, OpenSearch, and local JSON file backends.

## Backends

| Backend | Type String | Requires |
|---|---|---|
| Elasticsearch | `"elastic"` | `pip install elasticsearch` |
| OpenSearch | `"opensearch"` | `pip install opensearch-py` |
| Local JSON | `"local"` | (no dependencies) |

## Usage

```python
from commons.indexers import IndexerConfig, new_indexer

# Create config
config = IndexerConfig(
    type="elastic",                      # "elastic", "opensearch", or "local"
    servers=["http://localhost:9200"],    # ES/OpenSearch server URLs
    index="perf-results",                # Index name
    insecure_skip_verify=True,           # Skip TLS verification
    metrics_directory="/tmp/results",    # Output dir for local backend
)

# Create indexer via factory
indexer = new_indexer(config)

# Index documents
indexer.index([
    {"uuid": "run-123", "metricName": "post_query", "p99Latency": 42.5},
    {"uuid": "run-123", "metricName": "post_streaming", "p99Latency": 38.1},
])
```

## Features

### Document Deduplication

Elasticsearch and OpenSearch backends compute a SHA-256 hash of each document. Duplicate documents (identical content) are skipped automatically. This prevents double-indexing on re-runs.

### Local Backend

The local backend writes documents to `{metrics_directory}/{metric_name}.json`. If the file already exists, new documents are appended to the existing array.

```python
config = IndexerConfig(type="local", metrics_directory="/tmp/results")
indexer = new_indexer(config)
indexer.index([{"value": 42}], metric_name="latency")
# Writes to /tmp/results/latency.json
```

## API

### IndexerConfig

| Field | Type | Default | Description |
|---|---|---|---|
| `type` | str | `"elastic"` | Backend type |
| `servers` | list[str] | `[]` | Server URLs |
| `index` | str | `""` | Index name |
| `insecure_skip_verify` | bool | `True` | Skip TLS cert verification |
| `metrics_directory` | str | `"/tmp"` | Output dir for local backend |

### new_indexer(config) -> Indexer

Factory function. Returns the appropriate backend based on `config.type`.

### Indexer.index(documents, metric_name="")

Index a list of dicts. `metric_name` is used by the local backend for the output filename.
