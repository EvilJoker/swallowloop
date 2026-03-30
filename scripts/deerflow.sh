#!/bin/bash
# DeerFlow 管理脚本 - 使用官方 docker-compose-dev.yaml

set -e

DEERFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../vendor/deer-flow" && pwd)"
DEER_FLOW_ROOT="$DEERFLOW_DIR"
COMPOSE_CMD="docker compose -p deer-flow-dev -f docker-compose-dev.yaml"

usage() {
    echo "DeerFlow 管理脚本"
    echo ""
    echo "用法: $0 <command>"
    echo ""
    echo "命令:"
    echo "  start       启动 DeerFlow (Docker)"
    echo "  stop        停止 DeerFlow"
    echo "  restart     重启 DeerFlow"
    echo "  logs        查看 DeerFlow 日志"
    echo "  status      查看运行状态"
    echo ""
    echo "访问: http://localhost:2026"
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

# 准备配置文件
prepare_config() {
    cd "$DEERFLOW_DIR"

    # config.yaml 已存在，跳过
    if [ -f "config.yaml" ]; then
        echo "✓ config.yaml 已存在"
    else
        if [ -f "config.example.yaml" ]; then
            cp config.example.yaml config.yaml
            echo "✓ 已从 config.example.yaml 创建 config.yaml"
            echo "  请编辑 config.yaml 设置 API Key"
        fi
    fi

    # extensions_config.json
    if [ -f "extensions_config.json" ]; then
        echo "✓ extensions_config.json 已存在"
    else
        if [ -f "extensions_config.example.json" ]; then
            cp extensions_config.example.json extensions_config.json
            echo "✓ 已创建 extensions_config.json"
        else
            echo '{}' > extensions_config.json
            echo "✓ 已创建空的 extensions_config.json"
        fi
    fi
}

cmd_start() {
    check_docker
    echo "启动 DeerFlow..."

    prepare_config

    export DEER_FLOW_ROOT
    cd "$DEERFLOW_DIR/docker"
    $COMPOSE_CMD up -d --remove-orphans

    echo ""
    echo "DeerFlow 已启动!"
    echo "  🌐 访问地址: http://localhost:2026"
    echo "  📡 API Gateway: http://localhost:2026/api/*"
    echo "  🤖 LangGraph: http://localhost:2026/api/langgraph/*"
    echo ""
    echo "查看日志: $0 logs"
}

cmd_stop() {
    check_docker
    echo "停止 DeerFlow..."
    cd "$DEERFLOW_DIR/docker"
    $COMPOSE_CMD down
    echo "DeerFlow 已停止"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_logs() {
    cd "$DEERFLOW_DIR/docker"
    $COMPOSE_CMD logs -f
}

cmd_status() {
    cd "$DEERFLOW_DIR/docker"
    $COMPOSE_CMD ps
}

COMMAND="${1:-}"
case "$COMMAND" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    logs)
        shift
        cmd_logs "$@"
        ;;
    status)
        cmd_status
        ;;
    *)
        usage
        ;;
esac
