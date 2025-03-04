#!/usr/bin/env python2
# -*- coding: utf-8 -*-
from qingcloud import iaas
import time
import os
import sys
import config
import optparse
import socket
import ConfigParser

reload(sys)
sys.setdefaultencoding("utf-8")


def detect_port(ip,port):
    """检测ip上的端口是否开放
    """
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(1)
    return not s.connect_ex((ip,int(port)))

def retry(func, args=None, kw=None, timeout=150, step=5, check=lambda x : x):
    if args is None:
        args = []
    if kw is None:
        kw = {}
    end_time = int(time.time()) + timeout
    while end_time > time.time():
        result = func(*args, **kw)
        if check(result):
            return result
            break
        time.sleep(step)
    else:
        raise SystemError("timeout: {0.__name__}: args:{1} kw:{2} result: {3}".format(func, args, kw, result ))


def main():
    check_ret_code = lambda x : x.get("ret_code") == 0

    parser = optparse.OptionParser(usage='{0} [--reset] file1.yml [file2.yml [file3.yml]]'.format(sys.argv[0]))
    parser.add_option('--append', action='store_true', dest='append', default=False, help=u'给镜像添加脚本, 不重置系统')
    parser.add_option('--instances', action='store', dest='instances', help='主机instances,默认读取"config.py"', default=config.instances, metavar=config.instances)
    parser.add_option('--zone', action='store', dest='zone', help='区id, 默认读取config.ini', default=config.zone, metavar=config.zone)
    option, args = parser.parse_args()

    if not args:
        parser.error("not file")

    conn = iaas.connect_to_zone(option.zone, config.key, config.secret)

    # 重置系统
    if not option.append:
        conn.stop_instances(instances=[option.instances],force=True)
        print "reset_instances:", conn.reset_instances(instances=[option.instances], login_mode="keypair", login_keypair=config.keypair)
    # 等待重置成功后启动主机
    print "start_instances:", retry(conn.start_instances,kw={'instances': [option.instances], 'force': True} , check=check_ret_code)

    # 等待开放22端口
    for vxnet in conn.describe_instances(instances=[option.instances])['instance_set'][0]['vxnets']:
        ip = vxnet["private_ip"]
        retry(detect_port, args=(ip ,22))

    for yml in args:
        if not os.path.isfile(yml):
            raise SystemError("ERROR: '{0}'is not a file".format(yml))
        os.system("ansible-playbook " + yml)

    print "stop_instances:", conn.stop_instances(instances=[option.instances],force=True)
    print "capture_instance:", retry(conn.capture_instance, args=(option.instances,),
                                     kw={"image_name" : config.image_name}, check=check_ret_code)


if __name__ == '__main__':
    main()

