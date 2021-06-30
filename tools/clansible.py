#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from qingcloud import iaas
import os
import sys
import config
import subprocess
reload(sys)
sys.setdefaultencoding("utf-8")




def main():
    check_ret_code = lambda x : x.get("ret_code") == 0

    if len(sys.argv) < 3:
        raise SyntaxError('至少2个参数')

    cluseter = sys.argv[1]
    ansibleArgv = sys.argv[2:]
    # cluseter = "cl-dvmpwi5x"
    cluseterHosts = "/tmp/{0}.host".format(cluseter )

    conn = iaas.connect_to_zone(config.zone, config.key, config.secret)
    conn.describe_clusters(clusters=[cluseter])
    data = conn.describe_clusters(clusters=[cluseter])
    with open(cluseterHosts,'w' ) as f:
        f.write("[{0}]\n".format(cluseter))
        f.write('\n'.join(node["private_ip"] for node in data['cluster_set'][0]['nodes']))
    cmds =  "ansible {0} -i {1} {2}".format(cluseter, cluseterHosts, " ".join(ansibleArgv))
    print cmds
    # os.system(cmds)
    cmds = ["ansible", cluseter, "-i", cluseterHosts] + ansibleArgv

    subprocess.call(cmds)
    os.remove(cluseterHosts)



if __name__ == '__main__':
    main()

