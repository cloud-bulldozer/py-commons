""" metadata matcher
"""
import os
import sys
import logging
# pylint: disable=import-error
from elasticsearch7 import Elasticsearch
# pylint: disable=import-error
from elasticsearch.exceptions import NotFoundError
# pylint: disable=import-error
import pandas as pd


ES_URL = os.getenv("ES_SERVER")


class Matcher:
    """ Matcher
    """


    def __init__(self, index="perf_scale_ci", level=logging.INFO):
        self.index = index
        self.es_url = ES_URL
        self.search_size = 10000
        self.logger = logging.getLogger("Matcher")
        self.logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        # We can set the ES logging higher if we want additional debugging
        logging.getLogger("elasticsearch").setLevel(logging.WARN)
        self.es = Elasticsearch([self.es_url], timeout=30)
        self.data = None

    def get_metadata_by_uuid(self, uuid, index=None):
        """ get_metadata_by_uuid
        """
        if index is None:
            index = self.index
        query = {
            "query": {
                "match": {
                    "uuid": uuid
                }
            }
        }
        result = {}
        try:
            self.logger.info("Executing query against index %s",index)
            result = self.es.search(index=index, body=query)
            hits = result.get('hits', {}).get('hits', [])
            if hits:
                result = dict(hits[0]['_source'])
        except NotFoundError:
            print(f"UUID {uuid} not found in index {index}")
        return result

    def query_index(self, index, query):
        """ generic query function

        Args:
            index (str): _description_
            uuids (list): _description_
            query (str) : Query to make against ES
        """
        self.logger.info("Executing query against index=%s",index)
        self.logger.debug("Executing query \r\n%s",query)
        return self.es.search(index=index, body=query)

    def get_uuid_by_metadata(self, meta, index=None):
        """ get_uuid_by_metadata
        """
        if index is None:
            index = self.index
        version = meta["ocpVersion"][:4]
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": ' AND '.join([
                                    f'{field}: "{value}"' if isinstance(
                                        value, str) else f'{field}: {value}'
                                    for field, value in meta.items() if field != "ocpVersion"
                                ]) +
                                f' AND ocpVersion: {version}* AND jobStatus: success'
                            }
                        }
                    ]
                }
            },
            "size": self.search_size
        }
        result = self.query_index(index, query)
        hits = result.get('hits', {}).get('hits', [])
        uuids = [hit['_source']['uuid'] for hit in hits]
        return uuids

    def match_k8s_netperf(self, uuids):
        """_summary_

        Args:
            uuids (_type_): _description_
        """
        index = "k8s-netperf"
        ids = "\" OR uuid: \"".join(uuids)
        query = {
            "query": {
                "query_string": {
                    "query": (
                        f'( uuid: \"{ids}\" )'
                    )
                }
            },
            "size": self.search_size
        }
        result = self.query_index(index, query)
        runs = [item['_source'] for item in result["hits"]["hits"]]
        return runs

    def match_kube_burner(self, uuids):
        """ match kube burner runs
        Args:
            uuids (list): list of uuids
        Returns:
            list : list of runs
        """
        index = "ripsaw-kube-burner*"
        ids = "\" OR uuid: \"".join(uuids)
        query = {
            "query": {
                "query_string": {
                    "query": (
                        f'( uuid: \"{ids}\" )'
                        f' AND metricName: "jobSummary"'
                    )
                }
            },
            "size": self.search_size
        }
        result = self.query_index(index, query)
        runs = [item['_source'] for item in result["hits"]["hits"]]
        return runs

    def filter_runs(self, pdata, data):
        """ filter out runs with different jobIterations
        Args:
            pdata (_type_): _description_
            data (_type_): _description_
        Returns:
            _type_: _description_
        """
        columns = ['uuid', 'jobConfig.jobIterations']
        pdf = pd.json_normalize(pdata)
        pick_df = pd.DataFrame(pdf, columns=columns)
        iterations = pick_df.iloc[0]['jobConfig.jobIterations']
        df = pd.json_normalize(data)
        ndf = pd.DataFrame(df, columns=columns)
        ids_df = ndf.loc[df['jobConfig.jobIterations'] == iterations]
        return ids_df['uuid'].to_list()

    def burner_results(self, uuid, uuids, index):
        """ kube burner podReadyLatency
        Args:
            uuid (_type_): _description_
            uuids (_type_): _description_
            index (_type_): _description_
        Returns:
            _type_: _description_
        """
        if len(uuids) >= 1:
            if len(uuid) > 0:
                uuids.remove(uuid)
        if len(uuids) < 1:
            return []
        ids = "\" OR uuid: \"".join(uuids)
        query = {
            "query": {
                "query_string": {
                    "query": (
                        f'( uuid: \"{ids}\" )'
                        f' AND metricName: "podLatencyQuantilesMeasurement"'
                        f' AND quantileName: "Ready"'
                    )
                }
            },
            "size": self.search_size
        }
        result = self.query_index(index, query)
        runs = [item['_source'] for item in result["hits"]["hits"]]
        return runs

    def burner_cpu_results(self, uuids, namespace, index):
        """ kube burner CPU aggregated results for a namespace
        Args:
            uuids (_type_): _description_
            namespace (_type_): _description_
            index (_type_): _description_
        Returns:
            _type_: _description_
        """
        ids = "\" OR uuid: \"".join(uuids)
        query = {
            "aggs": {
                "time": {
                    "terms": {
                        "field": "uuid.keyword",
                        "size": self.search_size
                    },
                    "aggs": {
                        "time": {
                            "avg": {
                                "field": "timestamp"}
                        }
                    }
                },
                "uuid": {
                    "terms": {
                        "field": "uuid.keyword",
                        "size": self.search_size
                    },
                    "aggs": {
                        "cpu": {
                            "avg": {
                                "field": "value"
                            }
                        }
                    }
                }
            },
            "query": {
                "bool": {
                    "must": [{
                        "query_string": {
                            "query": (
                                f'( uuid: \"{ids}\" )'
                                f' AND metricName: "containerCPU"'
                                f' AND labels.namespace.keyword: {namespace}'
                            )
                        }
                    }]
                }
            },
            "size": self.search_size
        }
        runs = self.query_index(index, query)
        data = self.parse_burner_cpu_results(runs)
        return data

    def parse_burner_cpu_results(self, data: dict):
        """ parse out CPU data from kube-burner query
        Args:
            data (dict): _description_
        Returns:
            _type_: _description_
        """
        res = []
        stamps = data['aggregations']['time']['buckets']
        cpu = data['aggregations']['uuid']['buckets']
        for stamp in stamps:
            dat = {}
            dat['uuid'] = stamp['key']
            dat['timestamp'] = stamp['time']['value_as_string']
            acpu = next(item for item in cpu if item["key"] == stamp['key'])
            dat['cpu_avg'] = acpu['cpu']['value']
            res.append(dat)
        return res

    def convert_to_df(self, data, columns=None):
        """ convert to a dataframe
        Args:
            data (_type_): _description_
            columns (_type_, optional): _description_. Defaults to None.
        Returns:
            _type_: _description_
        """
        odf = pd.json_normalize(data)
        odf = odf.sort_values(by=['timestamp'])
        if columns is not None:
            odf = pd.DataFrame(odf, columns=columns)
        return odf

    def save_results(self, df, csv_file_path="output.csv", columns=None):
        """ write results to CSV
        Args:
            df (_type_): _description_
            csv_file_path (str, optional): _description_. Defaults to "output.csv".
            columns (_type_, optional): _description_. Defaults to None.
        """
        if columns is not None:
            df = pd.DataFrame(df, columns=columns)
        df.to_csv(csv_file_path)
