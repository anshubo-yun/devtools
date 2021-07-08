#!/usr/bin/python2
# -*- coding: utf-8 -*-
from qingcloud import iaas
import config
import sys
import optparse
# zones = ("sh1", "gd2", "pek3", "pek3a", "pekt3", "ap2a", "ap3")
reload(sys)
sys.setdefaultencoding("utf-8")
usage='''usage:
    {0} <vxnet_id> [e i-ff7duk1g [cl-cor1lnep]]
    {0} <vxnet_id> [exclude i-ff7duk1g [cl-cor1lnep]]'''.format(sys.argv[0])



if __name__ == '__main__':

    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-e', '--exclude', action='append', dest='exclude', help='排除的主机ID', default=[], metavar='i-bbgthwwo')
    parser.add_option('-z', '--zone', action='store', dest='zone', help='处理的区域 默认:{0}'.format(config.zone),
                      default=config.zone, metavar=config.zone)
    option, args = parser.parse_args()

    # if len(sys.argv) == 1 or (len(sys.argv) > 3 and sys.argv[2] not in [ "exclude", "e"]):
        # raise SystemExit(usage)
    vxnet = args[0]
    exclude = option.exclude

    # 连接zone
    conn = iaas.connect_to_zone(option.zone, config.key, config.secret)

    # 关闭集群
    data = conn.describe_clusters(status=["active"])
    for cluster_info in data["cluster_set"]:
        cluster = cluster_info.get("cluster_id")
        if cluster_info["vxnet"]["vxnet_id"] != vxnet:
            continue
        if cluster in exclude:
            continue
        if any(tag['tag_id'] in exclude for tag in cluster_info["tags"]):
            continue
        conn.stop_clusters(clusters=[cluster])

    # 关闭主机
    data = conn.describe_instances(status=["running"])
    for instance in data["instance_set"]:
        instance_id = instance.get("instance_id")
        if not vxnet in [ i['vxnet_id'] for i in instance['vxnets']]:
            continue
        if any(tag['tag_id'] in exclude for tag in instance["tags"]):
            continue
        if instance_id in exclude:
            continue
        conn.stop_instances(instances=[instance_id])

