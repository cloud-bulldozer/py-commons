"""
test_fmatch
"""

from datetime import datetime
import sys
import warnings

# pylint: disable=import-error
import pandas as pd

# pylint: disable=import-error
from matcher import Matcher

warnings.filterwarnings("ignore", message="Unverified HTTPS request.*")
warnings.filterwarnings(
    "ignore", category=UserWarning, message=".*Connecting to.*verify_certs=False.*"
)

match = Matcher(index="perf_scale_ci*", verify_certs=False)
res = match.get_metadata_by_uuid("b4afc724-f175-44d1-81ff-a8255fea034f")

meta = {}
meta["masterNodesType"] = "m6a.xlarge"
meta["workerNodesType"] = "m6a.xlarge"
meta["platform"] = "AWS"
meta["masterNodesCount"] = 3
meta["workerNodesCount"] = 6
meta["jobStatus"] = "success"
meta["ocpVersion"] = "4.17"
meta["networkType"] = "OVNKubernetes"
meta["benchmark.keyword"] = "cluster-density-v2"
# meta['encrypted'] = "true"
# meta['ipsec'] = "false"
# meta['fips'] = "false"

uuids = match.get_uuid_by_metadata(meta)
print("All uuids", len(uuids))
date = datetime.strptime("2024-07-01T13:46:24Z", "%Y-%m-%dT%H:%M:%SZ")
uuids2 = match.get_uuid_by_metadata(meta, lookback_date=date)
print("lookback uuids", len(uuids2))
uuids2 = match.get_uuid_by_metadata(meta)
if len(uuids) == 0:
    print("No UUID present for given metadata")
    sys.exit()
match = Matcher(index="ripsaw-kube-burner*", verify_certs=False)
runs = match.match_kube_burner(uuids)

ids = match.filter_runs(runs, runs)
podl_metrics = {
    "name": "podReadyLatency",
    "metricName": "podLatencyQuantilesMeasurement",
    "quantileName": "Ready",
    "metric_of_interest": "P99",
    "not": {"jobConfig.name": "garbage-collection"},
}
podl = match.get_results("", ids, metrics=podl_metrics)
kapi_metrics = {
    "name": "apiserverCPU",
    "metricName": "containerCPU",
    "labels.namespace.keyword": "openshift-kube-apiserver",
    "metric_of_interest": "value",
    "agg": {"value": "cpu", "agg_type": "avg"},
}
kapi_cpu = match.get_agg_metric_query(ids, metrics=kapi_metrics)
podl_df = match.convert_to_df(
    podl, columns=["uuid", "timestamp", "quantileName", "P99"]
)
kapi_cpu_df = match.convert_to_df(kapi_cpu)
merge_df = pd.merge(kapi_cpu_df, podl_df, on="uuid")
match.save_results(merge_df, "merged.csv", ["uuid", "timestamp_x", "cpu_avg", "P99"])

df = pd.read_csv("merged.csv")
ls = df["uuid"].to_list()
# Check merged csv data - Debug
for i in ls:
    # Debug - Ensure they are all using the same networkType
    print(match.get_metadata_by_uuid(i)["networkType"])
