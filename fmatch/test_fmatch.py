"""
test_fmatch
"""
import sys
# pylint: disable=import-error
import pandas as pd
# pylint: disable=import-error
from matcher import Matcher

match = Matcher(index='perf_scale_ci')

meta = {}
meta['benchmark'] = "cluster-density-v2"
meta['masterNodesType'] = "m6a.xlarge"
meta['workerNodesType'] = "m6a.xlarge"
meta['platform'] = "AWS"
meta['masterNodesCount'] = 3
meta['workerNodesCount'] = 24
meta['jobStatus'] = "success"
meta['ocpVersion'] = '4.15'
meta['networkType'] = "OVNKubernetes"
meta['encrypted'] = "true"
meta['ipsec'] = "false"
meta['fips'] = "false"

uuids = match.get_uuid_by_metadata(meta)
if len(uuids) == 0:
    print("No UUID present for given metadata")
    sys.exit()
runs = match.match_kube_burner(uuids)
ids = match.filter_runs(runs, runs)
podl = match.burner_results("", ids, "ripsaw-kube-burner*")

kapi_cpu = match.burner_cpu_results(
    ids, "openshift-kube-apiserver", "ripsaw-kube-burner*")
ovn_cpu = match.burner_cpu_results(
    ids, "openshift-ovn-kubernetes", "ripsaw-kube-burner*")
etcd_cpu = match.burner_cpu_results(
    ids, "openshift-etcd", "ripsaw-kube-burner*")

podl_df = match.convert_to_df(
    podl, columns=['uuid', 'timestamp', 'quantileName', 'P99'])
kapi_cpu_df = match.convert_to_df(kapi_cpu)
merge_df = pd.merge(kapi_cpu_df, podl_df, on="uuid")
match.save_results(merge_df, "merged.csv", [
                   "uuid", "timestamp_x", "cpu_avg", "P99"])
match.save_results(kapi_cpu_df, "CPUavg24.csv")
match.save_results(podl_df, "podlatency24.csv")

df = pd.read_csv("merged.csv")
ls = df["uuid"].to_list()
# Check merged csv data - Debug
for i in ls:
    # Debug - Ensure they are all using the same networkType
    print(match.get_metadata_by_uuid(i)['networkType'])
