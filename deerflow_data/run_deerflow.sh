#!/bin/bash
# DeerFlow 管理脚本
# 数据目录: ~/.deer-flow/
# 配置: config.yaml, extensions_config.json, skills/, logs/, .deer-flow/

set -e

DEER_FLOW_HOME="${HOME}/.deer-flow"
COMPOSE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-compose-dev.yaml"
COMPOSE_CMD="docker compose -p deer-flow-dev -f ${COMPOSE_FILE}"

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
    echo "数据目录: ${DEER_FLOW_HOME}"
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

# 初始化数据目录
init_data_dir() {
    if [ -d "${DEER_FLOW_HOME}" ]; then
        echo "✓ ${DEER_FLOW_HOME} 已存在"
    else
        echo "创建 ${DEER_FLOW_HOME} 目录..."
        mkdir -p "${DEER_FLOW_HOME}"
    fi

    # .deer-flow 目录（checkpoints 数据库）
    if [ -d "${DEER_FLOW_HOME}/.deer-flow" ]; then
        echo "✓ .deer-flow/ 已存在"
    else
        mkdir -p "${DEER_FLOW_HOME}/.deer-flow"
        echo "✓ 已创建 .deer-flow/ 目录"
    fi

    # config.yaml
    if [ -f "${DEER_FLOW_HOME}/config.yaml" ]; then
        echo "✓ config.yaml 已存在"
    else
        if [ -f "$(dirname ${COMPOSE_FILE})/config.yaml.template" ]; then
            cp "$(dirname ${COMPOSE_FILE})/config.yaml.template" "${DEER_FLOW_HOME}/config.yaml"
            echo "✓ 已从模板创建 config.yaml"
            echo "  请编辑 ${DEER_FLOW_HOME}/config.yaml 配置 API Key"
        else
            echo "错误: config.yaml.template 不存在"
            exit 1
        fi
    fi

    # .env
    if [ -f "${DEER_FLOW_HOME}/.env" ]; then
        echo "✓ .env 已存在"
    else
        if [ -f "$(dirname ${COMPOSE_FILE})/.env.template" ]; then
            cp "$(dirname ${COMPOSE_FILE})/.env.template" "${DEER_FLOW_HOME}/.env"
            echo "✓ 已从模板创建 .env"
            echo "  请编辑 ${DEER_FLOW_HOME}/.env 配置环境变量"
        else
            echo "警告: .env.template 不存在，跳过"
        fi
    fi

    # extensions_config.json
    if [ -f "${DEER_FLOW_HOME}/extensions_config.json" ]; then
        echo "✓ extensions_config.json 已存在"
    else
        if [ -f "$(dirname ${COMPOSE_FILE})/extensions_config.json" ]; then
            cp "$(dirname ${COMPOSE_FILE})/extensions_config.json" "${DEER_FLOW_HOME}/extensions_config.json"
            echo "✓ 已创建 extensions_config.json"
        else
            echo '{}' > "${DEER_FLOW_HOME}/extensions_config.json"
            echo "✓ 已创建空的 extensions_config.json"
        fi
    fi

    # skills 目录
    if [ -d "${DEER_FLOW_HOME}/skills" ]; then
        echo "✓ skills/ 已存在"
    else
        mkdir -p "${DEER_FLOW_HOME}/skills"
        echo "✓ 已创建 skills/ 目录"
    fi

    # logs 目录
    if [ -d "${DEER_FLOW_HOME}/logs" ]; then
        echo "✓ logs/ 已存在"
    else
        mkdir -p "${DEER_FLOW_HOME}/logs"
        echo "✓ 已创建 logs/ 目录"
    fi

    # nginx 配置目录
    if [ -d "${DEER_FLOW_HOME}/nginx" ]; then
        echo "✓ nginx/ 已存在"
    else
        mkdir -p "${DEER_FLOW_HOME}/nginx"
        echo "✓ 已创建 nginx/ 目录"
    fi
}

cmd_start() {
    check_docker
    echo "启动 DeerFlow..."
    echo "数据目录: ${DEER_FLOW_HOME}"

    init_data_dir

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
    $COMPOSE_CMD down
    echo "DeerFlow 已停止"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_logs() {
    $COMPOSE_CMD logs -f
}

cmd_status() {
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
