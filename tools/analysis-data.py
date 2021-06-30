#!/usr/bin/python2
# -*- coding: utf-8 -*-
import re
import csv
import sys
import time
import copy
from collections import defaultdict
reload(sys)
titleFormat = ["time", "CPU", "Memory", "Action", "Thread", "Size", "QPS", "latency90", "Latency", "Total", "status", "ThreadStatus", "STDOUT",  "STDERR"]

analysisFormat = ["CPU", "Memory", "Action", "QPS", "QPSThread", "Latency90", "Latency90Thread", "LatencyMax", "LatencyMaxThread"]

def csvWriterOpen(path, header):
    writerFile = open(path, 'w')
    csvWriter = csv.DictWriter(writerFile, fieldnames=header)
    csvWriter.writeheader()
    writerFile.flush()
    return writerFile, csvWriter

csvWriterFile, csvWriter = csvWriterOpen(time.strftime("redis-data-analysis_%Y-%m-%d_%H-%M-%S.csv"), titleFormat)
analysisFile,  analysisCsv = csvWriterOpen(time.strftime("redis-analysis_%Y-%m-%d_%H-%M-%S.csv"), analysisFormat)


datas = []
with open('redis-benchmark_count.csv', "r") as f:
    dictReader = csv.DictReader(f)
    for i in dictReader:
        if i["TOP"] == "average":
            continue
        for k in ("QPS", "Latency", "Total"):
            i[k] = float(i[k])
        i["STDOUT"] = "'" + i["STDOUT"]
        datas.append(i)



dataGroup = defaultdict(list)
threadGroup = defaultdict(list)

# 数据分组
for i, data in enumerate(datas):
    key = "CPU:{CPU:>2} Mem:{Memory:<2} Th:{Thread:<2} {Action} d:{Size}".format(**data)
    del data["TOP"] 
    data["status"] = [] 
    dataGroup[key].append(data)
    # print i, "{time} CPU:{CPU:>2} Mem:{Memory:<2} Th:{Thread:<2} {Action} d:{Size} QPS:{QPS:>9.2f} MaxL:{Latency:>6.2f} Total:{Total:>6.2f} top:{TOP}".format(**data)


for key, datas in dataGroup.items():
    total = copy.deepcopy(datas[0])
    del total['STDOUT'], total['STDERR']

    latencyMax = 0
    latency90  = 0
    qps = 0

    for k, data in enumerate(datas):
        find = re.search(r'^9\d\.\d+% <= (?P<latency>\d+(:?\.\d{,2})?) milliseconds$', data['STDOUT'], re.M)
        data["latency90"] = float(find.group('latency')) if not find is None else "0"
        qps = qps if data["QPS"] < datas[qps]["QPS"]  else k 
        latency90 = latency90 if data["latency90"] > datas[latency90]["latency90"]  else k 
        latencyMax = latencyMax if data["Latency"] > datas[latencyMax]["Latency"]  else k 

    datas[qps]["status"].append('QPS')
    datas[latency90]["status"].append('Latency90')
    datas[latencyMax]["status"].append('LatencyMax')
    for data in datas:
        data['status'] = ",".join(data['status'])
    
    csvWriter.writerows(datas)
    for k in ("QPS", "Latency", "Total", "latency90"):
        total[k] = sum(i[k] for i in datas) / len(datas)

    key = "CPU:{CPU:>2} Mem:{Memory:<2} {Action}".format(**total)
    threadGroup[key].append(total)


for key, datas in threadGroup.items():
    latencyMax = 0
    latency90  = 0
    qps = 0

    for k, data in enumerate(datas):
        data["ThreadStatus"] = []
        qps = qps if data["QPS"] < datas[qps]["QPS"]  else k 
        latency90 = latency90 if data["latency90"] > datas[latency90]["latency90"]  else k 
        latencyMax = latencyMax if data["Latency"] > datas[latencyMax]["Latency"]  else k 

    datas[qps]["ThreadStatus"].append('QPS')
    datas[latency90]["ThreadStatus"].append('Latency90')
    datas[latencyMax]["ThreadStatus"].append('LatencyMax')
    for data in datas:
        data['status'] = "total"
        data['ThreadStatus'] = ",".join(data['ThreadStatus'])
        # print "{time} CPU:{CPU:>2} Mem:{Memory:<2} Th:{Thread:<2} {Action} d:{Size} QPS:{QPS:>9.2f} MaxL:{Latency:>6.2f} Total:{Total:>6.2f} ".format(**data)
        csvWriter.writerow(data)

    analysisdata = { 'CPU' : data['CPU'] ,
                  'Memory' : data['Memory'],
                  'Action' : data['Action'],
                     'QPS' : datas[qps]['QPS'],
               'QPSThread' : datas[qps]['Thread'],
               'Latency90' : datas[latency90]['latency90'],
         'Latency90Thread' : datas[latency90]['Thread'],
              'LatencyMax' : datas[latencyMax]['Latency'],
        'LatencyMaxThread' : datas[latencyMax]['Thread']
                    }
    # print analysisdata 
    analysisCsv.writerow(analysisdata)
    
csvWriterFile.close()
analysisFile.close()  
