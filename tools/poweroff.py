#!/usr/bin/python2
# -*- coding: utf-8 -*-
from qingcloud import iaas
import config
import sys
usage='''usage:
    {0} <vxnet_id> [e i-ff7duk1g [cl-cor1lnep]]
    {0} <vxnet_id> [exclude i-ff7duk1g [cl-cor1lnep]]'''.format(sys.argv[0])

if __name__ == '__main__':
    if len(sys.argv) == 1 or (len(sys.argv) > 3 and sys.argv[2] not in [ "exclude", "e"]):
        raise SystemExit(usage)
    vxnet = sys.argv[1]
    exclude = sys.argv[3:]

    # 连接zone
    conn = iaas.connect_to_zone(config.zone , config.key, config.secret)

    # 关闭集群
    data = conn.describe_clusters(status=["active"])
    for cluster_info in data["cluster_set"]:
        if cluster_info["cluster_id"] not in exclude and cluster_info["vxnet"]["vxnet_id"] == vxnet:
            cluster = cluster_info.get("cluster_id")
            conn.stop_clusters(clusters=[cluster])

    # 关闭主机
    data = conn.describe_instances(status=["running"])
    for instance in data["instance_set"]:
        instance_id = instance["instance_id"]
        if instance_id in exclude:
            continue

        vxnets = [ i['vxnet_id'] for i in instance['vxnets']]
        if vxnet in vxnets:
            conn.stop_instances(instances=[instance_id])



