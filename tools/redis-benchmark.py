#!/usr/bin/python2
# -*- coding: utf-8 -*-
from qingcloud import iaas
import itertools
import config
import time
import socket
import subprocess as sp
import paramiko
import threading
import re
import csv
import os
import Queue
import logging
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

# logging.basicConfig(filename='my.log', level=logging.DEBUG, format=LOG_FORMAT)
# LOG_FORMAT = "%(levelname)s - %(message)s"
# LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
# logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
# logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

benchmark = "/opt/redis/current/redis-benchmark"
redisConf = "/data/redis/redis.conf"
toolHostList = [ "172.22.4.4", "172.22.4.15", "172.22.4.27", "172.22.4.28", "172.22.4.24"]
pkey = paramiko.RSAKey.from_private_key_file('/root/.ssh/id_rsa')
titleFormat = ["time", "CPU", "Memory", "Action", "Thread", "Size", "QPS", "Latency", "Total", "TOP", "STDOUT",  "STDERR"]

usage = """usage:
    {0} 1
    {0} 2
    {0} 4
    {0} 8
    {0} 16""".format(sys.argv[0])
actionList = ['get', "set"]
cluster_memory = {
        #    1 : "cl-nvl9r2ni",
           2 : "cl-s6bjdrnm",
           4 : "cl-15ukblty",
           8 : "cl-1mtvdw62",
          16 : "cl-9fnx0j9o",
          32 : "cl-egza18aj"
}
testInfoList = {
                 2 : { "cpu" :  2, "memory" :    (2, 4, 8, 16, 32), "thread" : (1, 2, 3)},
                 4 : { "cpu" :  4, "memory" :    (2, 4, 8, 16, 32), "thread" : (2, 3, 4)},
                 8 : { "cpu" :  8, "memory" :       (4, 8, 16, 32), "thread" : (4, 5, 6, 7, 8)},
                16 : { "cpu" : 16, "memory" :             (16, 32), "thread" : (6, 7, 8, 9, 10)}
               }
# dataSizeList = [64, 128, 256, 512, 1024]
dataSizeList = [64]

def sshConnect(host):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=host, port=22, username='root', pkey=pkey)
    return ssh

def runBenchmark(cpu, memory, th, ip, action, size, q=None, toolHost=None, startTime=None, timeout=600):
    find = re.compile(r'(?P<details>====== \w+ ======.*'
                      r'requests (:?total|completed) in (?P<total>\d+\.\d+) seconds.*<= (?P<latency>\d+) '
                      r'milliseconds\n(?P<qps>\d+.\d+) requests per second)', re.M|re.S)
    if startTime is None:
        startTime =time.strftime(r"%Y-%m-%d %H:%M:%S")
    result = {"time" : startTime,
               "CPU" : cpu,
            "Memory" : memory,
            "Action" : action,
              "Size" : size,
            "Thread" : th,
               "QPS" : 0,
           "Latency" : 0,
             "Total" : 0,
            "STDOUT" : "",
            "STDERR" : "",
               "TOP" : ""
             }

    cmds = []
    if not toolHost is None:
        cmds.extend(["ssh", toolHost])
    cmds.extend([benchmark,  "-h", ip, "-p", "6379", "-n", "3000000", "-r", "100000", "-c", "256", "-t", action, "-d", str(size), "--threads",  "16"])

    # print " ".join(cmds)
    try:
        proc = sp.Popen(cmds, stdout=sp.PIPE, stderr=sp.PIPE)
        retry(proc.poll, timeout=timeout, step=1, check=lambda x : not x is None)
    except SystemError as e:
        proc.kill()
        print " ".join(cmds)
        print e, e.args, proc.poll()
        print result 
        return result 
    stdout, stderr = proc.communicate()

    testReslt = find.search(stdout)
    if testReslt:
        result["QPS"] = float(testReslt.group('qps'))
        result["Latency"] = float(testReslt.group('latency'))
        result["Total"] = float(testReslt.group('total'))
        result["STDOUT"] = testReslt.group('details')
    else:
        result["STDOUT"] = stdout
    result["STDERR"] = stderr
    
    return result 

def setIoThreads(host, ioThreads):
    cmd = """grep -E "^io-threads \d" """ 
    ssh = sshConnect(host)
    stdin, stdout, stderr = ssh.exec_command('/bin/grep -E "^io-threads [0-9]+$" {conf}'.format(conf=redisConf))
    txt = stdout.read().strip()
    if txt: 
        ssh.exec_command('/bin/sed -i "/^io-threads /c io-threads {t}" {conf}'.format(conf=redisConf, t=ioThreads))
    else:
        ssh.exec_command('/bin/echo "io-threads-do-reads yes\nio-threads {t}" > {conf}'.format(conf=redisConf, t=ioThreads))
    ssh.exec_command('appctl stop;rm /data/redis/appendonly.aof -f;appctl start\n')
    ssh.close()
    return "io-thread", txt


def detect_port(ip,port):
    """检测ip上的端口是否开放"""
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex((ip,int(port)))
    # print "ip:{0} port:{1} code:{2}".format(ip, port, result)
    return not result

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
        time.sleep(step)
    else:
        raise SystemError("timeout: {0.__name__}: args:{1} kw:{2} result: {3}".format(func, args, kw, result ))


def startClusters(cluster):
    # 连接zone
    conn = iaas.connect_to_zone(config.zone , config.key, config.secret)
    data = conn.describe_clusters(clusters=[cluster])
    # 如果集群不存在则
    if data["total_count"] != 1:
        sys.stderr.write("find cluster Error\n")
        return False

    # 酌情启动集群
    status = data["cluster_set"][0]["status"] 
    nodes = data["cluster_set"][0]["nodes"]
    ips = [node["private_ip"] for node in nodes]
    if status == "stopped":
        conn.start_clusters(clusters=[cluster])
        for ip in ips:
            try:
                retry(detect_port, args=(ip ,6379))
            except SystemError as e:
                return False
    return ips 

def main(ipList, memory, threads, dataSizeList, actionList, toolHost, q):
    # 设置线程
    for threadNum, dataSize, action in itertools.product(threads, dataSizeList,  actionList):
        
        for ip in ipList:
            setIoThreads(ip, threadNum)
        time.sleep(5)

        resultList = []
        qpsTop = 0
        latencyTop = 0
        startTime = time.strftime(r"%H:%M:%S")
        average = {"time" : startTime,
                    "CPU" : cpu,
                 "Memory" : memory,
                 "Action" : action,
                   "Size" : dataSize,
                 "Thread" : threadNum,
                    "QPS" : 0,
                "Latency" : 0,
                  "Total" : 0,
                    "TOP" : "average"
                }
        for i in xrange(5):
            result = runBenchmark(cpu, memory, threadNum, ipList[0], action, dataSize, startTime=startTime, toolHost=toolHost)
            resultList.append(result)
            for k in ("QPS","Latency","Total"):
                average[k] += result[k]
            if resultList[qpsTop]["QPS"] < result["QPS"]:
                qpsTop = i
            if resultList[latencyTop]["Latency"] > result["Latency"]:
                latencyTop = i 
            time.sleep(5)
        if latencyTop == qpsTop:
            resultList[qpsTop]["TOP"] = "QPS,Latency"
        else:
            resultList[qpsTop]["TOP"] = "QPS"
            resultList[latencyTop]["TOP"] = "Latency"

        for i in ("QPS","Latency","Total"):
            average[i] /= 5
        resultList.append(average)
        q.put(resultList)


if __name__ == '__main__':
    # if len(sys.argv) != 2 or sys.argv[1] not in ("1", "2", "4", "8", "16",):
    #     raise SystemExit(usage)
    # cpu = int(sys.argv[1])
    cpu = 16
    # csvFilePath = time.strftime("%Y-%m-%d.csv".format(cpu))
    csvFilePath = time.strftime("redis-benchmark_%Y-%m-%d.csv")
    exists = os.path.exists(csvFilePath)

    csvFile = open(csvFilePath, "a+")
    csvWriter = csv.DictWriter(csvFile, fieldnames=titleFormat)
    if not exists:
        csvWriter.writeheader()

    queue = Queue.Queue()
    testInfo = testInfoList[cpu]
    threadList = []
    for memory, toolHost in zip(testInfo['memory'], toolHostList):
        #  查找并启动集群
        cluster = cluster_memory.get(memory)
        if memory is None:
            continue
        ips = startClusters(cluster)
        if not ips:
            continue
        threadList.append(threading.Thread(target=main, args=(ips, memory, testInfo['thread'], dataSizeList, actionList, toolHost, queue)))

    for th in threadList:
        th.start()
    
    while 1:
        try:
            resultList = queue.get(timeout=1)
        except Queue.Empty:
            if any(th.is_alive() for th in threadList):
                continue
            else:
                break

        for result in resultList:
            print "{time} CPU:{CPU:>2} Mem:{Memory:<2} Th:{Thread:<2} {Action} d:{Size} QPS:{QPS:>9.2f} MaxL:{Latency:>6.2f} Total:{Total:>6.2f} top:{TOP}".format(**result)
            csvWriter.writerow(result)
        csvFile.flush()
    csvFile.close()

