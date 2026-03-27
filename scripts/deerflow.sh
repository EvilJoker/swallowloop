#!/bin/bash
# DeerFlow 管理脚本

set -e

DEERFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../vendor/deer-flow" && pwd)"
DEERFLOW_HOME="${DEER_FLOW_HOME:-$DEERFLOW_DIR/backend/.deer-flow}"

usage() {
    echo "DeerFlow 管理脚本"
    echo ""
    echo "用法: $0 <command>"
    echo ""
    echo "命令:"
    echo "  config      生成本地配置文件"
    echo "  start       启动 DeerFlow (Docker)"
    echo "  stop        停止 DeerFlow"
    echo "  logs        查看 DeerFlow 日志"
    echo "  status      查看运行状态"
    echo "  setup       初始化沙箱镜像"
    echo ""
    echo "示例:"
    echo "  $0 config   # 首次使用需要先配置"
    echo "  $0 start    # 启动服务"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "错误: Docker 未安装"
        exit 1
    fi
    if ! docker info &> /dev/null; then
        echo "错误: Docker 未运行"
        exit 1
    fi
}

cmd_config() {
    echo "生成本地配置文件..."
    cd "$DEERFLOW_DIR"
    make config
}

cmd_start() {
    check_docker
    echo "启动 DeerFlow..."

    # 确保配置存在
    if [ ! -f "$DEERFLOW_DIR/config.yaml" ]; then
        echo "配置文件不存在，先运行 $0 config"
        cmd_config
    fi

    cd "$DEERFLOW_DIR/docker"
    docker-compose up -d
    echo ""
    echo "DeerFlow 已启动，访问 http://localhost:2026"
}

cmd_stop() {
    check_docker
    echo "停止 DeerFlow..."
    cd "$DEERFLOW_DIR/docker"
    docker-compose down
}

cmd_logs() {
    cd "$DEERFLOW_DIR/docker"
    docker-compose logs -f
}

cmd_status() {
    cd "$DEERFLOW_DIR/docker"
    docker-compose ps
}

cmd_setup() {
    check_docker
    echo "初始化沙箱镜像..."
    cd "$DEERFLOW_DIR"
    make setup-sandbox
}

COMMAND="${1:-}"
case "$COMMAND" in
    config)
        cmd_config
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    logs)
        cmd_logs
        ;;
    status)
        cmd_status
        ;;
    setup)
        cmd_setup
        ;;
    *)
        usage
        ;;
esac
