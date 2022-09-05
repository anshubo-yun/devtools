
> 这个脚本目前实现了 redis cluster 集群的压测, 目前不包括代理  以及 redis-sentinel 压测, 自动化脚本

*   benchmark 与 redis 集群 机器分开操作
    *   通常是多创建一个 K8S 节点, 然后给其打上污点
        *   好处 1. 在 k8s 集群内, 并且有网络组件, 这样可以直接压测 Pod IP 或者 cluster IP
        *   好处 2. 打了污点, 就可以保证集群不会跑在当前主机上, 可以保证 benchmark 与 redis 互不干扰

*   需要在部署了 K8S 主机上跑
*   当前主机要有 docker

**这个脚本目前实现了 redis cluster 集群的压测, 目前不包括代理  以及 redis-sentinel 压测, 自动化脚本**

#### **脚本下载: [redis-benchmark.tar.gz](https://wiki.yunify.com/download/attachments/128424945/redis-benchmark.tar.gz?version=6&modificationDate=1661327208945&api=v2)**

```
redis-benchmark
├── log                           <=== log 目录, 存放压测日志的地方
├── redis-cluster-predixy.sh      <=== redis-cluter 的 predixy 压测脚本
├── redis-cluster-predixy.yaml.d  <=== redis-cluster 集群给压测 predixy 的 yaml 存放目录 
├── redis-cluster.sh              <=== redis-cluster 压测脚本
├── redis-cluster.yaml.d          <=== redis-cluster 集群压测所需 yaml 存放目录(不包括predixy压测)
├── redis-sentinel.sh             <=== redis-sentinel 压测脚本
└── redis-sentinel.yaml.d         <=== redis-sentinel 集群 yaml 存放目录



```

脚本说明
----

    这个脚本, 需要大概修改参数, 然后直接执行, 好处是可以保留之前执行参数

```
#!/bin/bash
PASSWD="radondb@123"
# yaml 里 name

# yaml 里 namespace
NAME_SPACE="redis-cluster"

# 测试次数
TEST_TIMES=5

# 测试类型 空格分开
TEST_TYPE="SET GET"

# 测试数据大小 空格分开
TEST_SIZES="64 128 512 1024"

# redis节点数量
REPLICAS_COUNT=6


# -n 请求次数
BENCHMARK_REQUESTS=3000000

# -r key 个数
BENCHMARK_KEYSPACELEN=100000

# -c 模拟客户段个数
BENCHMARK_CLIENTS=512

# 线程数
BENCHMARK_THREADS=32

# REDIS  端口号
PORT="6379"

```

执行技巧
----

```sh
# 先启动个redis 容器, 给脚本使用 
docker run -d --rm --net host --name redis-benchmark --entrypoint=tail redis:6.2.5 -f


# 如果需要测试 TLS 则用如下命令
cd <tls文件所在目录>
docker run -d --rm --net host --name redis-benchmark --entrypoint tail -v $(pwd):/etc/redis/tls redis:6.2.5 -f

# 或
docker run -d --rm --net host --name redis-benchmark --entrypoint tail -v <tls文件所在目录>:/etc/redis/tls redis:6.2.5 -f

# tls 手动压测命令
redis-benchmark -h <redis host> -p <tls port> -a <密码> -n 10000000 -r 100000 -c 512 -t get,set -d 64 --threads 32 --cluster --tls --cert /etc/redis/tls/tls.crt --key /etc/redis/tls/tls.key --cacert /etc/redis/tls/ca.crt





# 启动
# 推荐使用 nohup xxx xxx xxx xxx 2>&1 & 方法
# nohup 作用是截获输出, 并落盘当前目录下的 nohup.out
# 2>&1 作用是将错误输出与标准输出合并, 由于有nohup, 会一同落盘到 nohup.out 里
# &> xxxx.log 用这个替换 2>&1 可以将所有日志输出到 xxxx.log


# 启动示例
nohup ./redis-cluster.sh 2>&1 &
# [1] 39631 <============================= 这个是启动 PID 
# nohup: ignoring input and appending output to 'nohup.out'


# 输出到特定位置
nohup ./redis-cluster.sh &> redis-cluster.20220812.log &
# [1] 39631 <============================= 这个是启动 PID 
# nohup: ignoring input and appending output to 'nohup.out'


# 查看压测进度
tail -f nohup.out
# 或
tail -f redis-cluster.20220812.log


# 关闭压测, 通过刚才获取pid 去中断掉, 实际跑完也会自动停止
kill 39631


# 检查输出内容是否正确
for log in log/*.log; do cat $log; echo $log; read; done
# 每查看一条按一次回车看下一条



# 查看输出QPS
awk '/throughput summary/{print FILENAME, $3}' log/*.log


# 关闭使用的容器
docker stop redis-benchmark



# 中断压测
# 关闭相对应进程
ps -ef | awk '/redis-(cluster|cluster-predixy|sentinel).sh/{print $2}' | xargs kill -9
# 重启容器, 达到清理进程目的
docker restart redis-benchmark


# 查看容器内进程, 没有 redis-benchmark 则说明被关掉了
docker exec -t redis-benchmark ps

```

