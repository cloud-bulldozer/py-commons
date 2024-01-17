"""
Unit Test file for fmatch.py
"""
#pylint: disable = redefined-outer-name
#pylint: disable = missing-function-docstring
#pylint: disable = import-error
import os

from elasticsearch.exceptions import NotFoundError
import pytest
import pandas as pd

#pylint: disable = import-error
from fmatch.matcher import Matcher


@pytest.fixture
def matcher_instance():
    sample_output = {
        "hits": {
            "hits": [
                {"_source": {"uuid": "uuid1", "field1": "value1"}},
                {"_source": {"uuid": "uuid2", "field1": "value2"}},
            ]
        }
    }
    match = Matcher(index="perf-scale-ci")
    match.es.search = lambda *args, **kwargs: sample_output
    return match


def test_get_metadata_by_uuid_found(matcher_instance):
    uuid = "test_uuid"
    result = matcher_instance.get_metadata_by_uuid(uuid)
    expected = {"uuid": "uuid1", "field1": "value1"}
    assert result == expected


def test_get_metadata_by_uuid_not_found(matcher_instance):
    def raise_exception():
        raise NotFoundError(404, "index_not_found_exception", "no such index [sample]")

    # Mock Elasticsearch response for testing NotFoundError
    matcher_instance.es.search = lambda *args, **kwargs: raise_exception()
    uuid = "nonexistent_uuid"
    result = matcher_instance.get_metadata_by_uuid(uuid=uuid, index="sample index")
    expected = {}
    assert result == expected


def test_query_index(matcher_instance):
    index = "test_uuid"
    query = "test_query"
    result = matcher_instance.query_index(index, query)
    expected = {
        "hits": {
            "hits": [
                {"_source": {"uuid": "uuid1", "field1": "value1"}},
                {"_source": {"uuid": "uuid2", "field1": "value2"}},
            ]
        }
    }
    assert result == expected


def test_get_uuid_by_metadata(matcher_instance):
    matcher_instance.es.search = lambda *args, **kwargs: {
        "hits": {
            "hits": [{"_source": {"uuid": "uuid1"}}, {"_source": {"uuid": "uuid2"}}]
        }
    }
    meta = {"field1": "value1", "ocpVersion": "4.15"}
    result = matcher_instance.get_uuid_by_metadata(meta)
    expected = ["uuid1", "uuid2"]
    assert result == expected


def test_match_k8s_netperf(matcher_instance):
    result = matcher_instance.match_k8s_netperf(["uuid1"])
    expected = [
        {"uuid": "uuid1", "field1": "value1"},
        {"uuid": "uuid2", "field1": "value2"},
    ]
    assert result == expected


def test_match_kube_bruner(matcher_instance):
    result = matcher_instance.match_kube_burner(["uuid1"])
    expected = [
        {"uuid": "uuid1", "field1": "value1"},
        {"uuid": "uuid2", "field1": "value2"},
    ]
    assert result == expected


def test_burner_results(matcher_instance):
    result = matcher_instance.burner_results(
        "uuid1", ["uuid1", "uuid1"], "sample_index"
    )
    expected = [
        {"uuid": "uuid1", "field1": "value1"},
        {"uuid": "uuid2", "field1": "value2"},
    ]
    assert result == expected


def test_burner_results_single_element(matcher_instance):
    result = matcher_instance.burner_results("uuid1", ["uuid1"], "sample_index")
    expected = []
    assert result == expected


def test_burner_cpu_results(matcher_instance):
    matcher_instance.parse_burner_cpu_results = lambda *args, **kwargs: {}
    result = matcher_instance.burner_cpu_results(
        ["uuid1", "uuid2"], "sample_namespace", "sample_index"
    )
    expected = {}
    assert result == expected


def test_filter_runs(matcher_instance):
    mock_data = [
        {
            "timestamp": "2024-01-15T20:00:46.307453873Z",
            "endTimestamp": "2024-01-15T20:30:57.853708171Z",
            "elapsedTime": 1812,
            "uuid": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "metricName": "jobSummary",
            "jobConfig": {
                "jobIterations": 216,
                "name": "cluster-density-v2",
                "jobType": "create",
                "qps": 20,
                "burst": 20,
                "namespace": "cluster-density-v2",
                "maxWaitTimeout": 14400000000000,
                "waitForDeletion": True,
                "waitWhenFinished": True,
                "cleanup": True,
                "namespacedIterations": True,
                "iterationsPerNamespace": 1,
                "verifyObjects": True,
                "errorOnVerify": True,
                "preLoadImages": True,
                "preLoadPeriod": 15000000000,
                "churn": True,
                "churnPercent": 10,
                "churnDuration": 1200000000000,
                "churnDelay": 120000000000,
            },
            "metadata": {
                "k8sVersion": "v1.28.5+c84a6b8",
                "ocpMajorVersion": "4.15",
                "ocpVersion": "4.15.0-0.nightly-2024-01-15-022811",
                "platform": "AWS",
                "sdnType": "OVNKubernetes",
                "totalNodes": 30,
            },
            "version": "1.7.12@f0b89ccdbeb2a7d65512f5970d5a25a82ec386b2",
        },
        {
            "timestamp": "2024-01-15T20:32:11.681417765Z",
            "endTimestamp": "2024-01-15T20:37:24.591361376Z",
            "elapsedTime": 313,
            "uuid": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "metricName": "jobSummary",
            "jobConfig": {"name": "garbage-collection"},
            "metadata": {
                "k8sVersion": "v1.28.5+c84a6b8",
                "ocpMajorVersion": "4.15",
                "ocpVersion": "4.15.0-0.nightly-2024-01-15-022811",
                "platform": "AWS",
                "sdnType": "OVNKubernetes",
                "totalNodes": 30,
            },
            "version": "1.7.12@f0b89ccdbeb2a7d65512f5970d5a25a82ec386b2",
        },
    ]
    result = matcher_instance.filter_runs(mock_data, mock_data)
    expected = ["90189fbf-7181-4129-8ca5-3cc8d656b595"]
    assert result == expected


def test_parse_burner_cpu_results(matcher_instance):
    mock_data = {"aggregations": {"time": {"buckets": []}, "uuid": {"buckets": []}}}
    mock_data["aggregations"]["time"]["buckets"] = [
        {
            "key": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "doc_count": 1110,
            "time": {
                "value": 1705349944941.3918,
                "value_as_string": "2024-01-15T20:19:04.941Z",
            },
        }
    ]
    mock_data["aggregations"]["uuid"]["buckets"] = [
        {
            "key": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "doc_count": 1110,
            "cpu": {"value": 10.818089329872935},
        }
    ]
    expected = [
        {
            "uuid": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "timestamp": "2024-01-15T20:19:04.941Z",
            "cpu_avg": 10.818089329872935,
        }
    ]
    result = matcher_instance.parse_burner_cpu_results(mock_data)
    assert result == expected


def test_convert_to_df(matcher_instance):
    mock_data = [
        {
            "uuid": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "timestamp": "2024-01-15T20:19:04.941Z",
            "cpu_avg": 10.818089329872935,
        }
    ]
    odf = pd.json_normalize(mock_data)
    expected = odf.sort_values(by=["timestamp"])
    result = matcher_instance.convert_to_df(
        mock_data, columns=["uuid", "timestamp", "cpu_avg"]
    )
    assert result.equals(expected)


def test_save_results(matcher_instance):
    mock_data = [
        {
            "uuid": "90189fbf-7181-4129-8ca5-3cc8d656b595",
            "timestamp": "2024-01-15T20:19:04.941Z",
            "cpu_avg": 10.818089329872935,
        }
    ]
    mock_file_name = "test_output.csv"
    mock_df = pd.json_normalize(mock_data)
    matcher_instance.save_results(
        mock_df, csv_file_path=mock_file_name, columns=["uuid", "timestamp", "cpu_avg"]
    )
    assert os.path.isfile(mock_file_name)
    os.remove(mock_file_name)


if __name__ == "__main__":
    pytest.main()
