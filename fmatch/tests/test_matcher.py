"""
Unit Test file for fmatch.py
"""

# pylint: disable = redefined-outer-name
# pylint: disable = missing-function-docstring
# pylint: disable = import-error, duplicate-code
import os
from unittest.mock import patch

from elasticsearch_dsl import Search
from elasticsearch_dsl.response import Response
import pytest
import pandas as pd

# pylint: disable = import-error
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
    with patch("fmatch.matcher.Elasticsearch") as mock_es:
        mock_es_instance = mock_es.return_value
        mock_es_instance.search.return_value = sample_output
        match = Matcher(index="perf-scale-ci")
        return match


def test_get_metadata_by_uuid_found(matcher_instance):
    uuid = "test_uuid"
    result = matcher_instance.get_metadata_by_uuid(uuid)
    expected = {"uuid": "uuid1", "field1": "value1"}
    assert result == expected


def test_query_index(matcher_instance):
    index = "test_index"
    search = Search(using=matcher_instance.es, index=index)
    result = matcher_instance.query_index(index, search)
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
    meta = {
        "field1": "value1",
        "ocpVersion": "4.15",
    }
    result = matcher_instance.get_uuid_by_metadata(meta)
    expected = ["uuid1", "uuid2"]
    assert result == expected


def test_match_kube_burner(matcher_instance):
    result = matcher_instance.match_kube_burner(["uuid1"])
    expected = [
        {"uuid": "uuid1", "field1": "value1"},
        {"uuid": "uuid2", "field1": "value2"},
    ]
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


def test_getResults(matcher_instance):
    test_uuid = "uuid1"
    test_uuids = ["uuid1", "uuid2"]
    test_metrics = {
        "name": "podReadyLatency",
        "metricName": "podLatencyQuantilesMeasurement",
        "quantileName": "Ready",
        "metric_of_interest": "P99",
        "not": {"jobConfig.name": "garbage-collection"},
    }
    result = matcher_instance.getResults(
        test_uuid, test_uuids, "test_index", test_metrics
    )
    expected = [
        {"uuid": "uuid1", "field1": "value1"},
        {"uuid": "uuid2", "field1": "value2"},
    ]
    assert result == expected


def test_get_agg_metric_query(matcher_instance):
    test_uuids = ["uuid1", "uuid2"]
    test_metrics = {
        "name": "apiserverCPU",
        "metricName": "containerCPU",
        "labels.namespace": "openshift-kube-apiserver",
        "metric_of_interest": "value",
        "agg": {"value": "cpu", "agg_type": "avg"},
    }
    data_dict = {
        "aggregations": {
            "time": {
                "buckets": [
                    {
                        "key": "uuid1",
                        "time": {"value_as_string": "2024-02-09T12:00:00"},
                    },
                    {
                        "key": "uuid2",
                        "time": {"value_as_string": "2024-02-09T13:00:00"},
                    },
                ]
            },
            "uuid": {
                "buckets": [
                    {"key": "uuid1", "cpu": {"value": 42}},
                    {"key": "uuid2", "cpu": {"value": 56}},
                ]
            },
        }
    }
    expected = [
        {"uuid": "uuid1", "timestamp": "2024-02-09T12:00:00", "cpu_avg": 42},
        {"uuid": "uuid2", "timestamp": "2024-02-09T13:00:00", "cpu_avg": 56},
    ]
    matcher_instance.query_index = lambda *args, **kwargs: Response(
        response=data_dict, search=data_dict
    )

    result = matcher_instance.get_agg_metric_query(
        test_uuids, "test_index", test_metrics
    )
    assert result == expected


def test_get_agg_metric_query_no_agg_values(matcher_instance):
    test_uuids = ["uuid1", "uuid2"]
    test_metrics = {
        "name": "apiserverCPU",
        "metricName": "containerCPU",
        "labels.namespace": "openshift-kube-apiserver",
        "metric_of_interest": "value",
        "agg": {"value": "cpu", "agg_type": "avg"},
    }
    data_dict = {
        "aggregations": {
            "time": {
                "buckets": [
                    {
                        "key": "uuid1",
                        "time": {"value_as_string": "2024-02-09T12:00:00"},
                    },
                    {
                        "key": "uuid2",
                        "time": {"value_as_string": "2024-02-09T13:00:00"},
                    },
                ]
            },
            "uuid": {"buckets": []},
        }
    }
    expected = [
        {"uuid": "uuid1", "timestamp": "2024-02-09T12:00:00", "cpu_avg": None},
        {"uuid": "uuid2", "timestamp": "2024-02-09T13:00:00", "cpu_avg": None},
    ]
    matcher_instance.query_index = lambda *args, **kwargs: Response(
        response=data_dict, search=data_dict
    )

    result = matcher_instance.get_agg_metric_query(
        test_uuids, "test_index", test_metrics
    )
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
