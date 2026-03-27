# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SwallowLoop（燕子回环）是一个围绕代码仓库的智能维护 Agent 系统。通过监听 GitHub Issue 并自动生成 PR 来完成代码任务。

## 开发命令

```bash
# 使用 run.sh 管理服务（必须使用）
./run.sh -backend     # 启动后端
./run.sh -frontend    # 启动前端
./run.sh              # 启动全部（后端+前端）
./run.sh stop         # 停止全部
./run.sh stop -backend # 停止后端
./run.sh restart      # 重启全部
./run.sh status       # 查看状态
./run.sh test         # 运行测试（后端+前端）

# 直接运行（仅开发调试用）
uv run swallowloop

# 运行测试（仅后端单元测试）
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_task_lifecycle.py -v

# 运行单个测试函数
pytest tests/test_task_lifecycle.py::TestTaskLifecycle::test_task_state_transitions -v
```

**重要**：优先使用 `run.sh` 管理服务，如果脚本有问题必须优先修复。

## 架构

采用 DDD 分层架构：

```
src/swallowloop/
├── domain/              # 领域层（零依赖）
│   ├── model/          # 领域模型
│   ├── repository/     # 仓库接口
│   ├── statemachine/   # 状态机
│   └── event/          # 领域事件
├── application/         # 应用层（依赖 domain）
│   ├── dto/           # 数据传输对象
│   └── service/        # 应用服务
├── infrastructure/     # 基础设施层（依赖 domain 接口）
│   ├── persistence/    # 持久化
│   ├── executor/       # 执行器
│   ├── agent/          # AI Agent
│   ├── config/         # 配置
│   ├── llm/           # 大模型配置
│   ├── logging/        # 日志
│   └── self_update/    # 自更新
└── interfaces/          # 接口层（依赖 application）
    └── web/            # Web API
```

### 接口规范

**修改代码前必须加载 `architecture-design` 技能**，确保遵守：
- 依赖方向规范（只能从外层指向内层）
- 接口约束（调用方只依赖抽象接口）
- 禁止事项（asyncio.run 在同步函数内等）

**运行契约检查**：
```bash
python .claude/skills/architecture-design/scripts/check_contracts.py
```

**架构设计技能**：使用 `architecture-design` skill 获取接口规范、依赖方向、契约检查和自检机制。详细说明见 `.claude/skills/architecture-design/SKILL.md`。

**修改检查清单**：
- [ ] 改动的代码在哪个模块？
- [ ] 这个模块的接口是谁？调用方是谁？
- [ ] 会不会破坏依赖方向？
- [ ] 需不需要同步修改调用方？
- [ ] 测试能发现这个问题吗？

### 模块命名规则

**所有模块必须在 `__init__.py` 中定义 `MODULE_NAME` 常量**：

```python
# 层级模块
MODULE_NAME = "domain"

# 子模块（层级.子模块）
MODULE_NAME = "domain.model"
MODULE_NAME = "infrastructure.persistence"
```

**规则**：
1. 每个有 `__init__.py` 的目录都是一个模块
2. 模块必须定义 `MODULE_NAME = "x.y.z"` 常量
3. `__all__` 列表中必须包含 `"MODULE_NAME"`
4. **新增模块必须经过开发者确认**，不能自行创建

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
- `mock`: 模拟 Agent（用于测试环境，固定延迟 5 秒）
- `deerflow`: 使用 DeerFlow 2.0（通过 HTTP API 与 DeerFlow 通信）

DeerFlow Agent 通过 HTTP API 与独立部署的 DeerFlow 通信，每个 Issue 对应一个 Thread。

## 多仓库支持

支持多仓库监听，通过 `GITHUB_REPOS` 配置（逗号分隔）。每个仓库有独立的 GitHubClient 和 SourceControlAdapter。

## LLM 配置

LLM 配置与 Agent 类型独立，支持通过 `LLM_PROVIDER`/`LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL_NAME` 环境变量配置。

## 关键设计

1. **Worker 进程**: 使用 `multiprocessing.Process` 执行任务，结果通过文件系统传递（`result-{issue_number}` 文件）
2. **并发控制**: Orchestrator 控制最大 Worker 数量，超出任务排队
3. **资源清理**: 任务完成后自动删除本地工作空间和远端分支
4. **持久化**: 使用 JSON 文件存储任务和工作空间，带文件锁

## Git Workflow

- Always confirm before running git push operations - show pending commits first
- **提交代码前必须确保 `run.sh test` 测试通过**

## Configuration

- When I mention a setting, always show me the exact file path and current value before making changes
- Before editing any config file, say: "Your current [setting name] in [file path] is [value]. I'll change it to [new value]. OK?"

## Working with URLs

- Before attempting browser/URL access, ask if I want to use web_search or WebFetch tools
- If my requested method isn't possible, say: "I can't do [X], but I can [alternative approach]. Want me to try that?"

## Tool Installation

- Before recommending plugins/tools: "Let me check your [tool] version first: [command]"

## 经验教训

项目经验教训存放在 `docs/lessons/` 目录。

**重要原则**：发现问题并解决后，必须反思为什么测试用例没有发现，并将根因分析记录到经验目录。

参考：`docs/lessons/README.md`
