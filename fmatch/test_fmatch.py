"""
test_fmatch
"""

import sys
# pylint: disable=import-error
import pandas as pd

# pylint: disable=import-error
from matcher import Matcher

match = Matcher(index="perf_scale_ci")
res=match.get_metadata_by_uuid("b4afc724-f175-44d1-81ff-a8255fea034f",'perf_scale_ci')

meta = {}
meta["masterNodesType"] = "m6a.xlarge"
meta["workerNodesType"] = "m6a.xlarge"
meta["platform"] = "AWS"
meta["masterNodesCount"] = 3
meta["workerNodesCount"] = 24
meta["jobStatus"] = "success"
meta["ocpVersion"] = "4.15"
meta["networkType"] = "OVNKubernetes"
meta["benchmark.keyword"] = "cluster-density-v2"
# meta['encrypted'] = "true"
# meta['ipsec'] = "false"
# meta['fips'] = "false"

uuids = match.get_uuid_by_metadata(meta)
if len(uuids) == 0:
    print("No UUID present for given metadata")
    sys.exit()
runs = match.match_kube_burner(uuids)

ids = match.filter_runs(runs, runs)
podl_metrics = {
    "name": "podReadyLatency",
    "metricName": "podLatencyQuantilesMeasurement",
    "quantileName": "Ready",
    "metric_of_interest": "P99",
    "not": {"jobConfig.name": "garbage-collection"},
}
podl = match.getResults("", ids, "ripsaw-kube-burner*",metrics=podl_metrics)
kapi_metrics = {
    "name": "apiserverCPU",
    "metricName": "containerCPU",
    "labels.namespace.keyword": "openshift-kube-apiserver",
    "metric_of_interest": "value",
    "agg": {"value": "cpu", "agg_type": "avg"},
}
kapi_cpu = match.get_agg_metric_query(ids, "ripsaw-kube-burner*", metrics=kapi_metrics)
podl_df = match.convert_to_df(
    podl, columns=['uuid', 'timestamp', 'quantileName', 'P99'])
kapi_cpu_df = match.convert_to_df(kapi_cpu)
merge_df = pd.merge(kapi_cpu_df, podl_df, on="uuid")
match.save_results(merge_df, "merged.csv", [
                   "uuid", "timestamp_x", "cpu_avg", "P99"])

df = pd.read_csv("merged.csv")
ls = df["uuid"].to_list()
# Check merged csv data - Debug
for i in ls:
    # Debug - Ensure they are all using the same networkType
    print(match.get_metadata_by_uuid(i)['networkType'])
