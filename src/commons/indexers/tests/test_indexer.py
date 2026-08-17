"""Tests for indexers module."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from commons.indexers.indexer import (
    IndexerConfig,
    LocalIndexer,
    OpenSearchIndexer,
    new_indexer,
)


class TestIndexerConfig(unittest.TestCase):
    """Test IndexerConfig initialization and defaults."""

    def test_defaults(self):
        """Test default config values."""
        config = IndexerConfig()
        self.assertEqual(config.type, "opensearch")
        self.assertEqual(config.servers, [])
        self.assertEqual(config.index, "")
        self.assertTrue(config.insecure_skip_verify)
        self.assertEqual(config.metrics_directory, "/tmp")

    def test_custom_values(self):
        """Test config with custom values."""
        config = IndexerConfig(
            type="elastic",
            servers=["https://es:9200"],
            index="MyIndex",
            insecure_skip_verify=False,
            metrics_directory="/data",
        )
        self.assertEqual(config.type, "elastic")
        self.assertEqual(config.servers, ["https://es:9200"])
        self.assertEqual(config.index, "myindex")
        self.assertFalse(config.insecure_skip_verify)
        self.assertEqual(config.metrics_directory, "/data")

    def test_index_lowercased(self):
        """Test that index name is lowercased."""
        config = IndexerConfig(index="MyIndex")
        self.assertEqual(config.index, "myindex")


class TestLocalIndexer(unittest.TestCase):
    """Test LocalIndexer file-based indexing."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._config = IndexerConfig(type="local", metrics_directory=self._tmpdir)

    def test_index_writes_json(self):
        """Test that documents are written to a JSON file."""
        indexer = LocalIndexer(self._config)
        docs = [{"metric": "cpu", "value": 42}]
        result = indexer.index(docs, metric_name="cpu-usage")

        out_path = os.path.join(self._tmpdir, "cpu-usage.json")
        self.assertTrue(os.path.exists(out_path))
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["value"], 42)
        self.assertIn("cpu-usage.json", result)

    def test_index_appends_to_existing(self):
        """Test that indexing appends to an existing file."""
        indexer = LocalIndexer(self._config)
        indexer.index([{"a": 1}], metric_name="test")
        indexer.index([{"b": 2}], metric_name="test")

        out_path = os.path.join(self._tmpdir, "test.json")
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)

    def test_index_empty_documents(self):
        """Test that empty document list returns early."""
        indexer = LocalIndexer(self._config)
        result = indexer.index([], metric_name="test")
        self.assertEqual(result, "No documents to index")

    def test_index_requires_metric_name(self):
        """Test that missing metric_name raises ValueError."""
        indexer = LocalIndexer(self._config)
        with self.assertRaises(ValueError):
            indexer.index([{"a": 1}], metric_name="")

    def test_creates_directory(self):
        """Test that metrics_directory is created if missing."""
        subdir = os.path.join(self._tmpdir, "nested", "dir")
        config = IndexerConfig(type="local", metrics_directory=subdir)
        LocalIndexer(config)
        self.assertTrue(os.path.isdir(subdir))


class TestOpenSearchIndexer(unittest.TestCase):
    """Test OpenSearchIndexer with mocked opensearch-py."""

    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_doc_hash_deterministic(self, mock_connect):
        """Test that identical documents produce the same hash."""
        config = IndexerConfig(servers=["https://es:9200"], index="test")
        indexer = OpenSearchIndexer(config)
        doc = {"key": "value", "num": 123}
        h1 = indexer._doc_hash(doc)
        h2 = indexer._doc_hash(doc)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_doc_hash_different_for_different_docs(self, mock_connect):
        """Test that different documents produce different hashes."""
        config = IndexerConfig(servers=["https://es:9200"], index="test")
        indexer = OpenSearchIndexer(config)
        h1 = indexer._doc_hash({"a": 1})
        h2 = indexer._doc_hash({"a": 2})
        self.assertNotEqual(h1, h2)

    @patch("opensearchpy.helpers.bulk", return_value=(2, []))
    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_dedup_skips_seen_documents(self, mock_connect, mock_bulk):
        """Test that duplicate documents are skipped in bulk indexing."""
        config = IndexerConfig(servers=["https://es:9200"], index="test")
        indexer = OpenSearchIndexer(config)
        indexer._client = MagicMock()

        docs = [{"a": 1}, {"a": 1}, {"a": 2}]
        indexer.index(docs)

        actions = mock_bulk.call_args[0][1]
        self.assertEqual(len(actions), 2)

    @patch("opensearchpy.helpers.bulk", return_value=(1, [{"index": {"error": "mapping"}}]))
    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_bulk_errors_logged(self, mock_connect, mock_bulk):
        """Test that bulk indexing errors are included in result message."""
        config = IndexerConfig(servers=["https://es:9200"], index="test")
        indexer = OpenSearchIndexer(config)
        indexer._client = MagicMock()

        result = indexer.index([{"a": 1}])
        self.assertIn("1 errors", result)

    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_index_empty_documents(self, mock_connect):
        """Test that empty document list returns early."""
        config = IndexerConfig(servers=["https://es:9200"], index="test")
        indexer = OpenSearchIndexer(config)
        result = indexer.index([])
        self.assertEqual(result, "No documents to index")


class TestNewIndexer(unittest.TestCase):
    """Test factory function new_indexer."""

    def test_local_type(self):
        """Test creating a local indexer."""
        config = IndexerConfig(type="local", metrics_directory=tempfile.mkdtemp())
        indexer = new_indexer(config)
        self.assertIsInstance(indexer, LocalIndexer)

    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_opensearch_type(self, mock_connect):
        """Test creating an opensearch indexer."""
        config = IndexerConfig(type="opensearch", servers=["https://es:9200"])
        indexer = new_indexer(config)
        self.assertIsInstance(indexer, OpenSearchIndexer)

    @patch("commons.indexers.indexer.OpenSearchIndexer._connect")
    def test_elastic_type(self, mock_connect):
        """Test that 'elastic' type creates an OpenSearchIndexer."""
        config = IndexerConfig(type="elastic", servers=["https://es:9200"])
        indexer = new_indexer(config)
        self.assertIsInstance(indexer, OpenSearchIndexer)

    def test_invalid_type_raises(self):
        """Test that unsupported type raises ValueError."""
        config = IndexerConfig(type="invalid")
        with self.assertRaises(ValueError):
            new_indexer(config)


if __name__ == "__main__":
    unittest.main()
