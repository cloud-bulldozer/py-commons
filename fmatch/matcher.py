""" metadata matcher
"""

# pylint: disable = invalid-name, invalid-unary-operand-type, no-member
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# pylint: disable=import-error
from elasticsearch import Elasticsearch


# pylint: disable=import-error
import pandas as pd
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.response import Response
from fmatch.logrus import SingletonLogger


class Matcher:
    """Matcher"""

    def __init__(
        self,
        index: str ="ospst-perf-scale-ci",
        level: int =logging.INFO,
        ES_URL: str =os.getenv("ES_SERVER"),
        verify_certs: bool =True,
    ):
        self.index = index
        self.es_url = ES_URL
        self.search_size = 10000
        self.logger = SingletonLogger(debug=level, name="Matcher")
        self.es = Elasticsearch([self.es_url], timeout=30, verify_certs=verify_certs)
        self.data = None

    def get_metadata_by_uuid(self, uuid: str, index: str = None) -> dict:
        """Returns back metadata when uuid is given

        Args:
            uuid (str): uuid of the run
            index (str, optional): index to be searched in. Defaults to None.

        Returns:
            _type_: _description_
        """
        if index is None:
            index = self.index
        query = Q("match", uuid=uuid)
        result = {}
        s = Search(using=self.es, index=index).query(query)
        res = self.query_index(index, s)
        hits = res.hits.hits
        if hits:
            result = dict(hits[0].to_dict()["_source"])
        return result

    def query_index(self, index: str, search: Search) -> Response:
        """generic query function

        Args:
            index (str): _description_
            search (Search) : Search object with query
        """
        self.logger.info("Executing query against index=%s", index)
        self.logger.debug("Executing query \r\n%s", search.to_dict())
        return search.execute()

    def get_uuid_by_metadata(
        self, meta: Dict[str, Any], index: str = None, lookback_date: datetime = None
    ) -> List[Dict[str, str]]:
        """get_uuid_by_metadata"""
        if index is None:
            index = self.index
        version = meta["ocpVersion"][:4]

        must_clause = [
            (
                Q("match", **{field: str(value)})
                if isinstance(value, str)
                else Q("match", **{field: value})
            )
            for field, value in meta.items()
            if field not in "ocpVersion"
        ]

        filter_clause = [
            Q("wildcard", ocpVersion=f"{version}*"),
            Q("match", jobStatus="success"),
        ]
        if isinstance(lookback_date, datetime):
            lookback_date = lookback_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if lookback_date:
            filter_clause.append(Q("range", timestamp={"gt": lookback_date}))
        query = Q(
            "bool",
            must=must_clause,
            filter=filter_clause,
        )
        s = Search(using=self.es, index=index).query(query).extra(size=self.search_size)
        result = self.query_index(index, s)
        hits = result.hits.hits
        uuids_docs = [
            {
                "uuid": hit.to_dict()["_source"]["uuid"],
                "buildUrl": hit.to_dict()["_source"]["buildUrl"],
            }
            for hit in hits
        ]
        return uuids_docs

    def match_kube_burner(self, uuids: List[str], index: str) -> List[Dict[str, Any]]:
        """match kube burner runs
        Args:
            uuids (list): list of uuids
        Returns:
            list : list of runs
        """
        query = Q(
            "bool",
            filter=[
                Q("terms", **{"uuid.keyword": uuids}),
                Q("match", metricName="jobSummary"),
                ~Q("match", **{"jobConfig.name": "garbage-collection"}),
            ],
        )
        search = (
            Search(using=self.es, index=index).query(query).extra(size=self.search_size)
        )
        result = self.query_index(index, search)
        runs = [item.to_dict()["_source"] for item in result.hits.hits]
        return runs

    def filter_runs(self, pdata: Dict[Any, Any], data: Dict[Any, Any]) -> List[str]:
        """filter out runs with different jobIterations
        Args:
            pdata (_type_): _description_
            data (_type_): _description_
        Returns:
            _type_: _description_
        """
        columns = ["uuid", "jobConfig.jobIterations"]
        pdf = pd.json_normalize(pdata)
        pick_df = pd.DataFrame(pdf, columns=columns)
        iterations = pick_df.iloc[0]["jobConfig.jobIterations"]
        df = pd.json_normalize(data)
        ndf = pd.DataFrame(df, columns=columns)
        ids_df = ndf.loc[df["jobConfig.jobIterations"] == iterations]
        return ids_df["uuid"].to_list()

    def getResults(
        self, uuid: str, uuids: List[str], index_str: str, metrics: Dict[str, Any]
    ) -> Dict[Any, Any]:
        """
        Get results of elasticsearch data query based on uuid(s) and defined metrics

        Args:
            uuid (str): _description_
            uuids (list): _description_
            index_str (str): _description_
            metrics (dict): _description_

        Returns:
            dict: Resulting data from query
        """
        if len(uuids) > 1 and uuid in uuids:
            uuids.remove(uuid)
        metric_queries = []
        not_queries = [
            ~Q("match", **{not_item_key: not_item_value})
            for not_item_key, not_item_value in metrics.get("not", {}).items()
        ]
        metric_queries = [
            Q("match", **{metric_key: metric_value})
            for metric_key, metric_value in metrics.items()
            if metric_key not in ["name", "metric_of_interest", "not"]
        ]
        metric_query = Q("bool", must=metric_queries + not_queries)
        query = Q(
            "bool",
            must=[
                Q("terms", **{"uuid.keyword": uuids}),
                metric_query,
            ],
        )
        search = (
            Search(using=self.es, index=index_str)
            .query(query)
            .extra(size=self.search_size)
        )
        result = self.query_index(index_str, search)
        runs = [item.to_dict()["_source"] for item in result.hits.hits]
        return runs

    def get_agg_metric_query(
        self, uuids: List[str], index: str, metrics: Dict[str, Any]
    ):
        """burner_metric_query will query for specific metrics data.

        Args:
            uuids (list): List of uuids
            index (str): ES/OS Index to query from
            metrics (dict): metrics defined in es index metrics
        """
        metric_queries = []
        not_queries = [
            ~Q("match", **{not_item_key: not_item_value})
            for not_item in metrics.get("not", [])
            for not_item_key, not_item_value in not_item.items()
        ]
        metric_queries = [
            Q("match", **{metric_key: metric_value})
            for metric_key, metric_value in metrics.items()
            if metric_key not in ["name", "metric_of_interest", "not", "agg"]
        ]
        metric_query = Q("bool", must=metric_queries + not_queries)
        query = Q(
            "bool",
            must=[
                Q("terms", **{"uuid.keyword": uuids}),
                metric_query,
            ],
        )
        search = (
            Search(using=self.es, index=index).query(query).extra(size=self.search_size)
        )
        agg_value = metrics["agg"]["value"]
        agg_type = metrics["agg"]["agg_type"]
        search.aggs.bucket(
            "time", "terms", field="uuid.keyword", size=self.search_size
        ).metric("time", "avg", field="timestamp")
        search.aggs.bucket(
            "uuid", "terms", field="uuid.keyword", size=self.search_size
        ).metric(agg_value, agg_type, field=metrics["metric_of_interest"])
        result = self.query_index(index, search)
        data = self.parse_agg_results(result, agg_value, agg_type)
        return data

    def parse_agg_results(
        self, data: Dict[Any, Any], agg_value: str, agg_type: str
    ) -> List[Dict[Any, Any]]:
        """parse out CPU data from kube-burner query
        Args:
            data (dict): Aggregated data from Elasticsearch DSL query
            agg_value (str): Aggregation value field name
            agg_type (str): Aggregation type (e.g., 'avg', 'sum', etc.)
        Returns:
            list: List of parsed results
        """
        res = []
        stamps = data.aggregations.time.buckets
        agg_buckets = data.aggregations.uuid.buckets

        for stamp in stamps:
            dat = {}
            dat["uuid"] = stamp.key
            dat["timestamp"] = stamp.time.value_as_string
            agg_values = next(
                (item for item in agg_buckets if item.key == stamp.key), None
            )
            if agg_values:
                dat[agg_value + "_" + agg_type] = agg_values[agg_value].value
            else:
                dat[agg_value + "_" + agg_type] = None
            res.append(dat)
        return res

    def convert_to_df(
        self, data: Dict[Any, Any], columns: List[str] = None
    ) -> pd.DataFrame:
        """convert to a dataframe
        Args:
            data (_type_): _description_
            columns (_type_, optional): _description_. Defaults to None.
        Returns:
            _type_: _description_
        """
        odf = pd.json_normalize(data)
        odf = odf.sort_values(by=["timestamp"])
        if columns is not None:
            odf = pd.DataFrame(odf, columns=columns)
        return odf

    def save_results(
        self,
        df: pd.DataFrame,
        csv_file_path: str = "output.csv",
        columns: List[str] = None,
    ) -> None:
        """write results to CSV
        Args:
            df (_type_): _description_
            csv_file_path (str, optional): _description_. Defaults to "output.csv".
            columns (_type_, optional): _description_. Defaults to None.
        """
        if columns is not None:
            df = pd.DataFrame(df, columns=columns)
        df.to_csv(csv_file_path)
