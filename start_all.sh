#!/bin/bash
# ====================================================
# MedVision-RAG 一键启动脚本
# 按依赖顺序启动所有服务，日志输出到各自的 .log 文件
# 启动顺序：环境变量 → Python AI → Java Backend → 网络检测 → Frontend → Dashboard
# ====================================================

# 获取脚本所在目录（即项目根目录）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$PROJECT_DIR/.service_pids" # 进程 PID 记录文件，用于 stop_all.sh 停止服务

echo "========================================"
echo "  MedVision-RAG 一键启动"
echo "  项目目录: $PROJECT_DIR"
echo "========================================"

# 清理上次遗留的 PID 文件
rm -f "$PID_FILE"

# ------------------------------------------
# 1. 加载 .env 环境变量
#    使 Java / Python 均能读到 INTERNAL_TOKEN 等配置
# ------------------------------------------
if [ -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "[1/6] 加载 .env 环境变量..."
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# ------------------------------------------
# 2. Python AI Service (port 8001)
#    耗时最长，最先启动
# ------------------------------------------
echo ""
echo "[2/6] 启动 Python AI Service (port 8001)..."

if [ -d "$PROJECT_DIR/backend-ai/venv" ]; then
    source "$PROJECT_DIR/backend-ai/venv/bin/activate"
fi

cd "$PROJECT_DIR/backend-ai"
nohup python main.py > "$PROJECT_DIR/backend-ai/service.log" 2>&1 &
PID_PYTHON=$!
echo "$PID_PYTHON" >> "$PID_FILE"
echo "  ✅ PID: $PID_PYTHON | 日志: backend-ai/service.log"

# 等待 Python AI Service 就绪
echo "  等待 Python AI Service 就绪..."
MAX_WAIT=120
WAITED=0
while ! curl -s http://localhost:8001/health > /dev/null 2>&1; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ⚠️  超时: Python 服务在 ${MAX_WAIT}s 内未就绪，仍继续启动"
        break
    fi
done
if [ $WAITED -lt $MAX_WAIT ]; then
    echo "  ✅ Python AI Service 已就绪 (等待 ${WAITED}s)"
fi

# ------------------------------------------
# 3. Java Backend (port 8080)
#    主控中心，连接 AI 和前端
# ------------------------------------------
echo ""
echo "[3/6] 启动 Java Backend (port 8080)..."

cd "$PROJECT_DIR/backend-java"
nohup mvn spring-boot:run > "$PROJECT_DIR/backend-java/backend.log" 2>&1 &
PID_JAVA=$!
echo "$PID_JAVA" >> "$PID_FILE"
echo "  ✅ PID: $PID_JAVA | 日志: backend-java/backend.log"

# 等待 Java Backend 就绪
echo "  等待 Java Backend 就绪..."
MAX_WAIT=120
WAITED=0
while ! curl -s http://localhost:8080/api/medicine/health > /dev/null 2>&1; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ⚠️  超时: Java 服务在 ${MAX_WAIT}s 内未就绪，仍继续启动"
        break
    fi
done
if [ $WAITED -lt $MAX_WAIT ]; then
    echo "  ✅ Java Backend 已就绪 (等待 ${WAITED}s)"
fi

# ------------------------------------------
# 4. 检测网络 IP，生成小程序配置
#    当前 IP + 热点备选，并行探测自动连接
# ------------------------------------------
echo ""
echo "[4/6] 检测网络 IP，生成小程序配置..."
ACTIVE_IPS=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | grep -v 198.18 | awk '{print $2}')
echo "  检测到 IP: $ACTIVE_IPS"

CONFIG_FILE="$PROJECT_DIR/frontend-wechat/config.js"
{
  echo "// ====================================================="
  echo "//  API_HOST 候选地址（自动生成，请勿手动编辑）"
  echo "//  小程序启动时并行探测，自动选择可用后端。"
  echo "// ====================================================="
  echo ""
  echo "const API_CANDIDATES = ["

  for IP in $ACTIVE_IPS; do
    echo "  'http://${IP}:8080',"
  done

  # 本地回退地址
  echo "  'http://localhost:8080',"
  echo "];"
  echo ""
  echo "module.exports = { API_CANDIDATES };"
} > "$CONFIG_FILE"
echo "  ✅ 已写入 $CONFIG_FILE"

# 快速验证：确保后端在检测到的 IP 上可达
for IP in $ACTIVE_IPS; do
    if curl -s -o /dev/null -w "" "http://${IP}:8080/api/medicine/health" 2>/dev/null; then
        echo "  ✅ 后端在 ${IP}:8080 可达"
    else
        echo "  ⚠️  后端在 ${IP}:8080 不可达，请检查网络"
    fi
done

# ------------------------------------------
# 5. Frontend HTTP Server (port 5174)
#    静态文件服务
# ------------------------------------------
echo ""
echo "[5/6] 启动 Frontend (port 5174)..."

cd "$PROJECT_DIR/frontend"
nohup python -m http.server 5174 > "$PROJECT_DIR/frontend/frontend_server.log" 2>&1 &
PID_FRONTEND=$!
echo "$PID_FRONTEND" >> "$PID_FILE"
echo "  ✅ PID: $PID_FRONTEND | 日志: frontend/frontend_server.log"

# ------------------------------------------
# 6. Admin Dashboard (port 8502)
#    监控仪表盘
# ------------------------------------------
echo ""
echo "[6/6] 启动 Admin Dashboard (port 8502)..."

cd "$PROJECT_DIR"
nohup streamlit run admin_dashboard.py --server.port 8502 --server.headless true > "$PROJECT_DIR/dashboard.log" 2>&1 &
PID_DASHBOARD=$!
echo "$PID_DASHBOARD" >> "$PID_FILE"
echo "  ✅ PID: $PID_DASHBOARD | 日志: dashboard.log"

# ------------------------------------------
# 启动汇总
# ------------------------------------------
echo ""
echo "========================================"
echo "  所有服务已启动！"
echo "========================================"
echo ""
echo "  Python AI Service : http://localhost:8001"
echo "  Java Backend       : http://localhost:8080"
echo "  Frontend           : http://localhost:5174"
echo "  Admin Dashboard    : http://localhost:8502"
echo ""
echo "  小程序候选地址:"
for IP in $ACTIVE_IPS; do
    echo "    http://${IP}:8080"
done
echo "    http://localhost:8080"
echo ""
echo "  提示: 使用 ./stop_all.sh 一键关闭所有服务"
echo "  日志: tail -f backend-ai/service.log"
echo "========================================"
