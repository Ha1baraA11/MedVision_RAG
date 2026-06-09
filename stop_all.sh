#!/bin/bash
# ====================================================
# MedVision-RAG 一键关闭脚本
# 双重关闭策略：PID 文件精确终止 + 端口扫描补漏（防止孤儿进程）
# ====================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/.service_pids" # start_all.sh 启动时写入的 PID 记录文件

echo "========================================"
echo "  MedVision-RAG 一键关闭"
echo "========================================"

ALL_CLEAN=true

# 方式一：从 PID 文件读取并终止
if [ -f "$PID_FILE" ]; then
    echo ""
    echo "  从 PID 文件读取进程..."
    while IFS= read -r PID; do
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            echo "  终止 PID: $PID"
            kill -9 "$PID" 2>/dev/null
            ALL_CLEAN=false
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
fi

# 方式二：按端口扫描补漏（防止漏掉 PID 文件中未记录的孤儿进程）
PORTS=(8001 8080 5174 8502)  # 四个服务的端口号
NAMES=("Python AI Service" "Java Backend" "Frontend" "Admin Dashboard")  # 对应服务名称

for i in "${!PORTS[@]}"; do
    PORT=${PORTS[$i]}
    NAME=${NAMES[$i]}

    PIDS=$(lsof -t -i:$PORT 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo ""
        echo "  关闭 $NAME (port $PORT)..."
        echo "     PID: $PIDS"
        echo "$PIDS" | xargs kill -9 2>/dev/null
        echo "  ✅ 已终止"
        ALL_CLEAN=false
    fi
done

echo ""
echo "========================================"
if [ "$ALL_CLEAN" = true ]; then
    echo "  所有服务已关闭，无残留进程。"
else
    echo "  所有服务已关闭！"
fi
echo "========================================"
