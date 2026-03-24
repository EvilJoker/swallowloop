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

    if is_running "$BACKEND_PID_FILE"; then
        echo "Backend is already running (PID: $(cat $BACKEND_PID_FILE))"
        return 1
    fi

    echo "Starting backend on port $BACKEND_PORT..."
    > "$BACKEND_LOG_FILE"  # 清空日志
    cd /media/vdc/github/swallowloop && uv run python -c "from swallowloop.main import run_server; run_server(port=$BACKEND_PORT)" > "$BACKEND_LOG_FILE" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    echo "Backend started (PID: $(cat $BACKEND_PID_FILE))"
}

# 启动前端
start_frontend() {
    load_env_ports
    ensure_log_dir

    if is_running "$FRONTEND_PID_FILE"; then
        echo "Frontend is already running (PID: $(cat $FRONTEND_PID_FILE))"
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

# 停止后端
stop_backend() {
    stop_process "$BACKEND_PID_FILE" "Backend"
}

# 停止前端
stop_frontend() {
    stop_process "$FRONTEND_PID_FILE" "Frontend"
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
    echo "=== SwallowLoop Status ==="

    echo -n "Backend:  "
    if is_running "$BACKEND_PID_FILE"; then
        local pid=$(cat $BACKEND_PID_FILE)
        local start_time=$(ps -o lstart= -p "$pid" 2>/dev/null || echo "unknown")
        echo "Running (PID: $pid, Started: $start_time)"
    else
        echo "Stopped"
    fi

    echo -n "Frontend: "
    if is_running "$FRONTEND_PID_FILE"; then
        local pid=$(cat $FRONTEND_PID_FILE)
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
    status)
        status
        ;;
    test)
        run_tests
        ;;
    *)
        echo "Usage: run.sh [-all|-backend|-frontend|restart|stop|status]"
        echo ""
        echo "Commands:"
        echo "  -all       Start both backend and frontend (default)"
        echo "  -backend   Start only backend"
        echo "  -frontend  Start only frontend"
        echo "  restart    Restart services"
        echo "  stop       Stop services"
        echo "  status     Show service status"
        echo "  test       Run all tests (backend + frontend)"
        echo ""
        echo "Examples:"
        echo "  run.sh -all          # Start both services"
        echo "  run.sh restart       # Restart both services"
        echo "  run.sh stop -backend # Stop only backend"
        exit 1
        ;;
esac
