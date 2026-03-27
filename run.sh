#!/bin/bash
# SwallowLoop 启动脚本

set -e

# 项目根目录
PROJECT_ROOT="/media/vdc/github/swallowloop"

# 日志目录
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$LOG_DIR"

# 默认端口
DEFAULT_BACKEND_PORT=9500
DEFAULT_FRONTEND_PORT=9501

# Watchdog 检测间隔（秒）
WATCHDOG_INTERVAL=30

# 端口配置（从 .env 读取）
load_env_ports() {
    local env_file="$PROJECT_ROOT/.env"
    if [ -f "$env_file" ]; then
        BACKEND_PORT=$(grep -E "^BACKEND_PORT=" "$env_file" 2>/dev/null | cut -d'=' -f2)
        FRONTEND_PORT=$(grep -E "^FRONTEND_PORT=" "$env_file" 2>/dev/null | cut -d'=' -f2)
    fi
    BACKEND_PORT=${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}
    FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}
}

# PID 文件路径
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# 日志文件路径
BACKEND_LOG_FILE="$LOG_DIR/backend.log"
FRONTEND_LOG_FILE="$LOG_DIR/frontend.log"

# 确保日志目录存在
ensure_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
    fi
}

# 检查进程是否在运行
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        # PID 文件存在但进程已退出，清理
        rm -f "$pid_file"
    fi
    return 1
}

# 启动后端
start_backend() {
    load_env_ports
    ensure_log_dir

    # 优先用端口检测（更可靠，防止 PID 文件错乱）
    if is_port_in_use "$BACKEND_PORT"; then
        local existing_pid=$(get_port_pid "$BACKEND_PORT")
        echo "Backend is already running on port $BACKEND_PORT (PID: $existing_pid)"
        # 更新 PID 文件为正确的进程
        if [ -n "$existing_pid" ]; then
            echo "$existing_pid" > "$BACKEND_PID_FILE"
        fi
        return 1
    fi

    echo "Starting backend on port $BACKEND_PORT..."
    > "$BACKEND_LOG_FILE"  # 清空日志
    cd /media/vdc/github/swallowloop && uv run swallowloop --port $BACKEND_PORT > "$BACKEND_LOG_FILE" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    echo "Backend started (PID: $(cat $BACKEND_PID_FILE))"
}

# 启动前端
start_frontend() {
    load_env_ports
    ensure_log_dir

    # 优先用端口检测（更可靠，防止 PID 文件错乱）
    if is_port_in_use "$FRONTEND_PORT"; then
        local existing_pid=$(get_port_pid "$FRONTEND_PORT")
        echo "Frontend is already running on port $FRONTEND_PORT (PID: $existing_pid)"
        # 更新 PID 文件为正确的进程
        if [ -n "$existing_pid" ]; then
            echo "$existing_pid" > "$FRONTEND_PID_FILE"
        fi
        return 1
    fi

    echo "Starting frontend on port $FRONTEND_PORT..."
    > "$FRONTEND_LOG_FILE"  # 清空日志
    cd /media/vdc/github/swallowloop/frontend && npm run dev -- --port $FRONTEND_PORT > "$FRONTEND_LOG_FILE" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    echo "Frontend started (PID: $(cat $FRONTEND_PID_FILE))"
}

# 停止进程
stop_process() {
    local pid_file=$1
    local name=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $name (PID: $pid)..."
            # 先尝试杀进程组（如果它是会话头）
            kill -9 -"$pid" 2>/dev/null || true
            # 再杀进程本身
            kill -9 "$pid" 2>/dev/null || true
            rm -f "$pid_file"
            echo "$name stopped"
        else
            echo "$name is not running"
            rm -f "$pid_file"
        fi
    else
        echo "$name is not running (no PID file)"
    fi
}

# 通过端口找到并杀死进程
kill_by_port() {
    local port=$1
    local name=$2
    local pid=$(lsof -i:$port -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing $name on port $port (PIDs: $pid)..."
        echo "$pid" | xargs kill -9 2>/dev/null || true
        return 0
    fi
    return 1
}

# 停止后端
stop_backend() {
    load_env_ports
    # 优先用端口杀死（更可靠，因为 uv run wrapper 和 Python 子进程关系复杂）
    if kill_by_port "$BACKEND_PORT" "Backend"; then
        # 成功杀死
        rm -f "$BACKEND_PID_FILE"
        return 0
    fi
    # 端口没有被占用，说明已经停止了
    rm -f "$BACKEND_PID_FILE"
    return 0
}

# 停止前端
stop_frontend() {
    load_env_ports
    # 优先用端口杀死（更可靠）
    if kill_by_port "$FRONTEND_PORT" "Frontend"; then
        # 成功杀死
        rm -f "$FRONTEND_PID_FILE"
        return 0
    fi
    # 端口没有被占用，说明已经停止了
    rm -f "$FRONTEND_PID_FILE"
    return 0
}

# 检查端口是否被占用
is_port_in_use() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        # -sTCP:LISTEN 只获取监听状态的连接
        lsof -i:$port -sTCP:LISTEN >/dev/null 2>&1
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln 2>/dev/null | grep -q ":$port "
    else
        # 备用方法：直接尝试连接
        (echo >/dev/tcp/localhost/$port) 2>/dev/null
    fi
}

# 获取端口对应的进程 PID（只取 LISTEN 状态的）
get_port_pid() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -i:$port -sTCP:LISTEN -t 2>/dev/null | head -1
    fi
}

# Watchdog 模式：检测并重启崩溃的服务
watchdog() {
    echo "=== Watchdog Mode ==="
    echo "Interval: ${WATCHDOG_INTERVAL}s"
    echo "Press Ctrl+C to stop"
    echo "Note: Run 'run.sh stop' to stop all services"

    while true; do
        # 检查后端
        if ! is_port_in_use "$BACKEND_PORT"; then
            echo "[$(date '+%H:%M:%S')] Backend is down, restarting..."
            start_backend
        fi

        # 检查前端
        if ! is_port_in_use "$FRONTEND_PORT"; then
            echo "[$(date '+%H:%M:%S')] Frontend is down, restarting..."
            start_frontend
        fi

        sleep "$WATCHDOG_INTERVAL"
    done
}

# 运行测试
run_tests() {
    echo "Running tests..."
    cd /media/vdc/github/swallowloop

    # 后端测试
    echo "=== Backend Tests ==="
    uv run pytest tests/ -v --tb=short
    BACKEND_RESULT=$?

    # 前端测试
    echo "=== Frontend Tests ==="
    cd /media/vdc/github/swallowloop/frontend
    npm run test:run
    FRONTEND_RESULT=$?

    cd /media/vdc/github/swallowloop

    if [ $BACKEND_RESULT -ne 0 ] || [ $FRONTEND_RESULT -ne 0 ]; then
        echo "=== Tests Failed ==="
        if [ $BACKEND_RESULT -ne 0 ]; then
            echo "Backend tests failed (exit code: $BACKEND_RESULT)"
        fi
        if [ $FRONTEND_RESULT -ne 0 ]; then
            echo "Frontend tests failed (exit code: $FRONTEND_RESULT)"
        fi
        return 1
    fi

    echo "=== All Tests Passed ==="
    return 0
}

# 查看状态
status() {
    load_env_ports
    echo "=== SwallowLoop Status ==="

    echo -n "Backend:  "
    if is_port_in_use "$BACKEND_PORT"; then
        local pid=$(get_port_pid "$BACKEND_PORT")
        local start_time=$(ps -o lstart= -p "$pid" 2>/dev/null || echo "unknown")
        echo "Running (PID: $pid, Started: $start_time)"
    else
        echo "Stopped"
    fi

    echo -n "Frontend: "
    if is_port_in_use "$FRONTEND_PORT"; then
        local pid=$(get_port_pid "$FRONTEND_PORT")
        local start_time=$(ps -o lstart= -p "$pid" 2>/dev/null || echo "unknown")
        echo "Running (PID: $pid, Started: $start_time)"
    else
        echo "Stopped"
    fi
}

# 主命令处理（无参数时默认 -all）
case "${1:-}" in
    ""|-all)
        start_backend
        start_frontend
        ;;
    -backend)
        start_backend
        ;;
    -frontend)
        start_frontend
        ;;
    restart)
        shift
        case "$1" in
            -all|"")
                stop_backend
                stop_frontend
                sleep 1
                start_backend
                start_frontend
                ;;
            -backend)
                stop_backend
                sleep 1
                start_backend
                ;;
            -frontend)
                stop_frontend
                sleep 1
                start_frontend
                ;;
            *)
                echo "Unknown option for restart: $1"
                echo "Usage: run.sh restart [-all|-backend|-frontend]"
                exit 1
                ;;
        esac
        ;;
    stop)
        shift
        case "$1" in
            -all|"")
                stop_backend
                stop_frontend
                ;;
            -backend)
                stop_backend
                ;;
            -frontend)
                stop_frontend
                ;;
            *)
                echo "Unknown option for stop: $1"
                echo "Usage: run.sh stop [-all|-backend|-frontend]"
                exit 1
                ;;
        esac
        ;;
    watchdog)
        watchdog
        ;;
    status)
        status
        ;;
    test)
        run_tests
        ;;
    *)
        echo "Usage: run.sh [-all|-backend|-frontend|restart|stop|watchdog|status]"
        echo ""
        echo "Commands:"
        echo "  -all       Start both backend and frontend (default)"
        echo "  -backend   Start only backend"
        echo "  -frontend  Start only frontend"
        echo "  restart    Restart services"
        echo "  stop       Stop services"
        echo "  watchdog   Watchdog mode (auto-restart crashed services, 30s interval)"
        echo "  status     Show service status"
        echo "  test       Run all tests (backend + frontend)"
        echo ""
        echo "Examples:"
        echo "  run.sh -all          # Start both services"
        echo "  run.sh watchdog      # Start in watchdog mode (auto-restart)"
        echo "  run.sh restart       # Restart both services"
        echo "  run.sh stop -backend # Stop only backend"
        exit 1
        ;;
esac
