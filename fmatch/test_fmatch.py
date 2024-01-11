from matcher import Matcher
import pandas as pd
import json



match=Matcher(index='perf_scale_ci')

df=pd.read_csv("merged.csv")
ls=df["uuid"].to_list()

for i in ls:
    print(match.get_metadata_by_uuid(i)["networkType"])
    #print(json.dumps(match.get_metadata_by_uuid(i),sort_keys=False, indent=4))

meta={}
meta['benchmark']="cluster-density-v2"
#meta['masterNodesType'] = "m6a.4xlarge"
meta['masterNodesType'] = "m6a.xlarge"
meta['workerNodesType'] = "m6a.xlarge"
meta['platform']="AWS"
meta['masterNodesCount']=3
meta['workerNodesCount']=24
meta['jobStatus']="success"
meta['ocpVersion']='4.15'
meta['networkType']="OVNKubernetes"


uuids=match.get_uuid_by_metadata(meta)
if len(uuids)==0:
    print("No UUID present for given metadata")
    exit()
#print(uuids)
#print("5eb93cb1-5db1-41cd-997d-4a35741e3236" in uuids)
runs=match.match_kube_burner(uuids)
#print("ef1b328b-1843-43f4-8529-5f4b6ceaadaf" in uuids)
#print(runs)
ids=match.filter_runs(runs,runs)
podl=match.burner_results("",ids,"ripsaw-kube-burner*")

kapi_cpu=match.burner_cpu_results(ids,"openshift-kube-apiserver","ripsaw-kube-burner*")
ovn_cpu=match.burner_cpu_results(ids,"openshift-ovn-kubernetes","ripsaw-kube-burner*")
etcd_cpu=match.burner_cpu_results(ids,"openshift-etcd","ripsaw-kube-burner*")


podl_df=match.convert_to_df(podl,columns=['uuid','timestamp', 'quantileName', 'P99'])
kapi_cpu_df=match.convert_to_df(kapi_cpu)
merge_df=pd.merge(kapi_cpu_df,podl_df,on="uuid")
match.save_results(merge_df,"merged.csv",["uuid","timestamp_x","cpu_avg","P99"])
match.save_results(kapi_cpu_df,"CPUavg24.csv")
match.save_results(podl_df,"podlatency24.csv")
# cdf = pd.json_normalize(cdf)
# cdf = cdf.sort_values(by=['timestamp'])
# cdf.to_csv("output2.csv")
#match.saveResults(nrs)
#match.saveResults(nrs2,"output2.csv")

# #print(json.dumps(runs[0],sort_keys=False, indent=4))
# for run in runs:
#     print(json.dumps(run,indent=4))

