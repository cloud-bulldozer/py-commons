"""
commons.indexers - Multi-Backend Metrics Indexer

Pluggable indexing library supporting OpenSearch/Elasticsearch and
local JSON file backends with factory pattern, SHA-256 document
deduplication, and bulk indexing.
"""

from commons.indexers.indexer import (
    IndexerConfig,
    Indexer,
    OpenSearchIndexer,
    LocalIndexer,
    new_indexer,
)

__all__ = [
    "IndexerConfig",
    "Indexer",
    "OpenSearchIndexer",
    "LocalIndexer",
    "new_indexer",
]
