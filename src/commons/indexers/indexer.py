import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger("commons.indexers")


class IndexerConfig:
    """Indexer configuration.

    Attributes:
        type: Backend type - "elastic", "opensearch", or "local".
              "elastic" and "opensearch" both use the opensearch-py client.
        servers: List of server URLs for ES/OpenSearch backends.
        index: Index name for ES/OpenSearch backends.
        insecure_skip_verify: Disable TLS certificate verification.
        metrics_directory: Output directory for local backend.
    """

    def __init__(
        self,
        type="opensearch",
        servers=None,
        index="",
        insecure_skip_verify=True,
        metrics_directory="/tmp",
    ):
        self.type = type
        self.servers = servers or []
        self.index = index.lower() if index else ""
        self.insecure_skip_verify = insecure_skip_verify
        self.metrics_directory = metrics_directory


class Indexer(ABC):
    """Abstract base for all indexer backends."""

    @abstractmethod
    def index(self, documents, metric_name=""):
        """Index a list of documents.

        Args:
            documents: List of dicts to index.
            metric_name: Metric name used by local backend for filename.

        Returns:
            Status string summarizing the indexing result.
        """


class OpenSearchIndexer(Indexer):
    """OpenSearch/Elasticsearch backend using opensearch-py.

    Works with both OpenSearch and Elasticsearch servers.
    Uses bulk indexing and SHA-256 document deduplication.
    """

    def __init__(self, config):
        self._config = config
        self._seen_hashes = set()
        self._client = None
        self._connect()

    def _connect(self):
        try:
            from opensearchpy import OpenSearch

            server = self._config.servers[0] if self._config.servers else ""
            if not server:
                raise ValueError("No server configured")
            logger.debug("Connecting to %s", server)
            self._client = OpenSearch(
                [server],
                verify_certs=not self._config.insecure_skip_verify,
                ssl_show_warn=False,
                timeout=600,
            )
            health = self._client.cluster.health()
            status = health.get("status", "unknown")
            if status == "red":
                raise RuntimeError("Cluster health is RED")
            logger.info(
                "Connected to OpenSearch at %s (cluster status: %s)",
                server,
                status,
            )
            if self._config.index and not self._client.indices.exists(
                index=self._config.index
            ):
                self._client.indices.create(index=self._config.index)
                logger.info("Created index: %s", self._config.index)
        except ImportError:
            raise RuntimeError(
                "opensearch-py package not installed: pip install opensearch-py"
            )

    @staticmethod
    def _doc_hash(document):
        raw = json.dumps(document, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    def index(self, documents, metric_name=""):
        if not documents:
            return "No documents to index"
        try:
            from opensearchpy.helpers import bulk

            actions = []
            skipped = 0
            for doc in documents:
                doc_hash = self._doc_hash(doc)
                if doc_hash in self._seen_hashes:
                    skipped += 1
                    continue
                self._seen_hashes.add(doc_hash)
                actions.append({
                    "_index": self._config.index,
                    "_id": doc_hash,
                    "_source": doc,
                })
            if actions:
                success, errors = bulk(self._client, actions, raise_on_error=False)
                msg = (
                    f"Indexed {success} documents to "
                    f"{self._config.servers[0]}/{self._config.index} "
                    f"(skipped {skipped} duplicates, {len(errors)} errors)"
                )
            else:
                msg = f"All {skipped} documents were duplicates, nothing indexed"
            logger.info(msg)
            return msg
        except ImportError:
            raise RuntimeError(
                "opensearch-py package not installed: pip install opensearch-py"
            )


class LocalIndexer(Indexer):
    """Local JSON file backend.

    Writes documents to {metrics_directory}/{metric_name}.json.
    Appends to existing files if they exist.
    """

    def __init__(self, config):
        self._config = config
        os.makedirs(config.metrics_directory, exist_ok=True)

    def index(self, documents, metric_name=""):
        if not documents:
            return "No documents to index"
        if not metric_name:
            raise ValueError("metric_name is required for local indexing")
        out_path = os.path.join(self._config.metrics_directory, f"{metric_name}.json")
        existing = []
        if os.path.exists(out_path):
            try:
                with open(out_path) as f:
                    data = json.load(f)
                    existing = data if isinstance(data, list) else [data]
            except (json.JSONDecodeError, IOError):
                existing = []
        existing.extend(documents)
        with open(out_path, "w") as f:
            json.dump(existing, f, indent=2)
        msg = f"Local index: {len(documents)} documents written to {out_path}"
        logger.info(msg)
        return msg


def new_indexer(config):
    """Create an indexer for the configured backend.

    Args:
        config: IndexerConfig with type, servers, index, etc.

    Returns:
        Indexer instance for the configured backend.

    Raises:
        ValueError: If config.type is not a supported backend.
        RuntimeError: If the backend's client library is not installed.
    """
    indexer_type = config.type.lower()
    if indexer_type in ("elastic", "opensearch"):
        return OpenSearchIndexer(config)
    elif indexer_type == "local":
        return LocalIndexer(config)
    else:
        raise ValueError(f"Indexer not found: {config.type}")
