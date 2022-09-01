#!/bin/bash
PASSWD="radondb@123"
# yaml 里 name
NAME="redis-sentinel"
# yaml 里 namespace
NAME_SPACE="redis-sentinel"

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
# 脚本路径, 不必修改
SCRIPT_PATH="$(realpath ${0%/*})"

#SCRIPT_PATH="${0%/*}"
#echo $SCRIPT_PATH
PID=$$

wathNodeHost(){
  local text ret=0
  while true; do
    text="$(kubectl get svc -n "${NAME_SPACE}" "${NAME}-master" -o jsonpath='{.spec.clusterIP}')"
    if [[  -n "$text" ]]; then
      echo "$text"
      return
    fi
    sleep 2
  done
}


wathCreateCluster() {
  while [[ "$(kubectl get -n "${NAME_SPACE}" redissentinels.redis.radondb.com "${NAME}" -o jsonpath='{.status.state}' )" != "Running" ]] ;do
    sleep 5
  done
}

#set -x
OLD_PID="$(ps -ef | awk '/redis-(cluster|cluster-predixy|sentinel).sh/ && $0!~/'$PID'/{print $2}')"
if [[ -n "$OLD_PID" ]]; then
  ps -ef | awk '/redis-(cluster|cluster-predixy|sentinel).sh/ && $0!~/'$PID'/{print}'
  echo "有压测进程在跑 PID: "${OLD_PID}", 可以直接kill掉进程, 如下"
  echo "kill -9 "$OLD_PID
  exit
fi

for yaml in ${SCRIPT_PATH}/redis-sentinel.yaml.d/*.yaml; do
  # 部署新集群
  basenameYaml=$(basename "${yaml%.yaml}")
  echo "部署: ${yaml}"
  kubectl apply -f "$yaml"
  wathCreateCluster
  node=$(wathNodeHost)
  echo "开始压测 ${yaml} ${node} ${PORT}"
  for (( i = 0; i < TEST_TIMES ; ++i)); do
    for size in ${TEST_SIZES}; do
      for action in ${TEST_TYPE} ; do
        echo "压测 $yaml $action $i $size"
        {
          date +"Start Time: %F %H:%M:%S"
          docker exec -t redis-benchmark redis-benchmark \
              -h $node -p $PORT -a "$PASSWD" \
              -n "${BENCHMARK_REQUESTS}" -r "${BENCHMARK_KEYSPACELEN}" \
              -c "${BENCHMARK_CLIENTS}" --threads "${BENCHMARK_THREADS}" \
              -t "${action}" -d "${size}"
          date +"End Time: %F %H:%M:%S"
        } &> log/${basenameYaml}-${action}-${size}-${i}.log
        sleep 10
      done
      #sleep 10
    done
  done

  # 删除老集群
  kubectl delete -f "$yaml"
  # 等待删除完成
  while [[ "$(kubectl get pod  -n ${NAME_SPACE} 2>&1)" != *"No resources found"* ]] ; do
    sleep 10
  done
done
