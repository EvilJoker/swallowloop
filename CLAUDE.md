# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SwallowLoop（燕子回环）是一个围绕代码仓库的智能维护 Agent 系统。通过监听 GitHub Issue 并自动生成 PR 来完成代码任务。

## 开发命令

```bash
# 安装依赖
uv sync

# 运行
uv run swallowloop

# 运行测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_task_lifecycle.py -v

# 运行单个测试函数
pytest tests/test_task_lifecycle.py::TestTaskLifecycle::test_task_state_transitions -v
```

## 架构

采用 DDD 分层架构：

```
src/swallowloop/
├── interfaces/          # 接口层
│   ├── cli/orchestrator.py   # 主调度器，协调 TaskService 和 ExecutionService
│   └── web/dashboard.py      # Web Dashboard (FastAPI)
├── application/         # 应用层
│   ├── dto/             # 数据传输对象
│   └── service/        # 应用服务
│       ├── task_service.py      # 任务生命周期管理
│       └── execution_service.py  # Worker 进程管理、超时检测
├── domain/              # 领域层（核心业务逻辑，无外部依赖）
│   ├── model/task.py   # Task 聚合根，使用 transitions 状态机
│   ├── model/workspace.py
│   ├── model/comment.py
│   ├── model/pull_request.py
│   └── repository/     # 仓库接口定义
└── infrastructure/      # 基础设施层
    ├── agent/          # Agent 实现 (IFlow/Aider)
    ├── config/         # 配置管理 (Settings)
    ├── persistence/    # JSON 文件持久化
    ├── source_control/ # GitHub API 封装
    └── self_update.py  # 自更新机制
```

## 任务状态机

Task 使用 transitions 库实现状态机，核心状态流转：

```
new → assigned → pending → in_progress → submitted → completed
                              ↑               ↓
                              └─── retry ◄───┘
```

状态定义在 `domain/model/enums.py` 的 `TaskState`。

## Agent 系统

两种 Agent 类型，通过 `AGENT_TYPE` 配置：
- `iflow`: 使用 iflow-cli-sdk
- `aider`: 使用 aider-chat

Agent 负责在 Workspace 中执行代码任务，通过 `agent.execute(task, workspace_path)` 调用。

## 多仓库支持

支持多仓库监听，通过 `GITHUB_REPOS` 配置（逗号分隔）。每个仓库有独立的 GitHubClient 和 SourceControlAdapter。

## LLM 配置

LLM 配置与 Agent 类型独立，支持通过 `LLM_PROVIDER`/`LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL_NAME` 环境变量配置。

## 关键设计

1. **Worker 进程**: 使用 `multiprocessing.Process` 执行任务，结果通过文件系统传递（`result-{issue_number}` 文件）
2. **并发控制**: Orchestrator 控制最大 Worker 数量，超出任务排队
3. **资源清理**: 任务完成后自动删除本地工作空间和远端分支
4. **持久化**: 使用 JSON 文件存储任务和工作空间，带文件锁
