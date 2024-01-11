from elasticsearch7 import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import pandas as pd

import os
import csv
import json 

ES_URL=os.getenv("ES_SERVER")

class Matcher:
    def __init__(self, index="perf_scale_ci"):
        self.index=index
        self.es_url=ES_URL
        self.es=Elasticsearch([self.es_url],http_auth=["username","password"])
        self.data=None

    def get_metadata_by_uuid(self,uuid,index=None):
        if index==None:
            index=self.index
        query = {
        "query": {
            "match": {
                "uuid": uuid
                }
            }
        }
        try:
            result = self.es.search(index=index, body=query)
            hits = result.get('hits', {}).get('hits', [])
            if hits:
                return dict(hits[0]['_source'])
            else:
                return None
        except NotFoundError:
            print(f"UUID {uuid} not found in index {index}")
            return None


    def get_uuid_by_metadata(self,meta,index=None):
        if index==None:
            index=self.index
        version=meta["ocpVersion"][:4]
        query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": ' AND '.join([
                                f'{field}: "{value}"' if isinstance(value, str) else f'{field}: {value}'
                                for field, value in meta.items() if field!="ocpVersion"
                            ]) +
                            f' AND ocpVersion: {version}* AND jobStatus: success'
                        }
                    }
                ]
            }
        },
        "size": 10000
        }
        result = self.es.search(index=index, body=query)
        hits = result.get('hits', {}).get('hits', [])
        uuids=[hit['_source']['uuid'] for hit in hits]
        return uuids
    
    def match_kube_burner(self,uuids):
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
            "size":10000
        }
        result=self.es.search(index=index,body=query)
        runs = [item['_source'] for item in result["hits"]["hits"]]
        return runs

    def filter_runs(self,pdata,data):
        columns = ['uuid','jobConfig.jobIterations']
        pdf = pd.json_normalize(pdata)
        pick_df = pd.DataFrame(pdf, columns=columns)
        iterations = pick_df.iloc[0]['jobConfig.jobIterations']
        df = pd.json_normalize(data)
        ndf = pd.DataFrame(df, columns=columns)
        ids_df = ndf.loc[df['jobConfig.jobIterations'] == iterations ]
        return ids_df['uuid'].to_list()
    
    def burner_results(self,uuid,uuids,index):
        if len(uuids) > 1 :
            if len(uuid) > 0 :
                uuids.remove(uuid)
        if len(uuids) < 1 :
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
            "size":10000
        }
        result=self.es.search(index=index,body=query)
        runs = [item['_source'] for item in result["hits"]["hits"]]
        return runs
    
    def burner_cpu_results(self,uuids,namespace,index):
        ids = "\" OR uuid: \"".join(uuids)
        query = {
            "aggs": {
                "time": {
                "terms": {
                    "field": "uuid.keyword",
                    "size":10000
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
                    "size":10000
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
            "size":10000
        }
        runs=self.es.search(index=index,body=query)
        data=self.parse_burner_cpu_results(runs)
        return data
    
    def parse_burner_cpu_results(self,data: dict):
        res = []
        stamps = data['aggregations']['time']['buckets']
        cpu = data['aggregations']['uuid']['buckets']
        for stamp in stamps :
            dat = {}
            dat['uuid'] = stamp['key']
            dat['timestamp'] = stamp['time']['value_as_string']
            acpu = next(item for item in cpu if item["key"] == stamp['key'])
            dat['cpu_avg'] = acpu['cpu']['value']
            res.append(dat)
        return res
    
    def convert_to_df(self,data,columns=None):
        odf = pd.json_normalize(data)
        if columns!=None:
            odf = pd.DataFrame(odf, columns=columns)
        odf = odf.sort_values(by=['timestamp'])
        return odf


    def save_results(self,df,csv_file_path="output.csv",columns=None):
        if columns!=None:
            df = pd.DataFrame(df, columns=columns)
        df.to_csv(csv_file_path)

