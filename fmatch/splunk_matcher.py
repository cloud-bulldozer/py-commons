# pylint: disable = C0209, R0913, E0401
"""
Matcher for splunk datasource
"""
from typing import Dict, Any
import orjson
from splunklib import client, results


class SplunkMatcher:
    """Splunk data source matcher"""

    def __init__(
        self, host: str, port: int, username: str, password: str, indice: str
    ):  # pylint: disable = R0917
        self.indice = indice
        self.service = client.connect(
            host=host, port=port, username=username, password=password
        )

    async def query(
        self, query: Dict[Any, Any], searchList: str = "", max_results: int = 10000
    ):
        """
        Query data from splunk server using splunk lib sdk

        Args:
            query (string): splunk query
            OPTIONAL: searchList (string): additional query parameters for index
        """
        query["count"] = max_results

        # If additional search parameters are provided, include those in searchindex
        searchindex = (
            "search index={} {}".format(self.indice, searchList)
            if searchList
            else "search index={}".format(self.indice)
        )
        try:
            oneshotsearch_results = self.service.jobs.oneshot(searchindex, **query)
        except Exception as e:  # pylint: disable = W0718
            print("Error querying splunk: {}".format(e))
            return None

        # Get the results and display them using the JSONResultsReader
        res_array = []
        async for record in self._stream_results(oneshotsearch_results):
            try:
                res_array.append(
                    {
                        "data": orjson.loads(record["_raw"]),  # pylint: disable = E1101
                        "host": record["host"],
                        "source": record["source"],
                        "sourcetype": record["sourcetype"],
                        "bucket": record["_bkt"],
                        "serial": record["_serial"],
                        "timestamp": record["_indextime"],
                    }
                )
            except Exception as e:  # pylint: disable = W0718
                print(f"Error on including Splunk record query in results array: {e}")

        return res_array

    async def _stream_results(self, oneshotsearch_results: Any) -> Any:
        for record in results.JSONResultsReader(oneshotsearch_results):
            yield record

    async def close(self):
        """Closes splunk client connections"""
        await self.service.logout()
