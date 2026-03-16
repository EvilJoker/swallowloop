# SwallowLoop 架构文档

## 项目概述

**SwallowLoop · 燕子回环**：围绕代码仓库的智能维护 Agent 系统。

### 项目愿景

为程序员个人/小团队提供一个常驻的开发 Agent 系统：只需配置仓库地址和 API Key，就能在不改变现有 Git 工作流的前提下，模拟「有一个远程实习生帮你写代码」。

### 核心设计思想

1. **围绕仓库打转，而不是取代开发者** - 一切改动都以 PR 的形式交付，人类保留最终审批权
2. **最小侵入：兼容现有 Git/GitHub 流程** - 在现有流程之上增加一层「自动劳动」
3. **安全优先：隔离+审计** - 所有自动改动只发生在 Agent 专用分支，主仓只接受 PR
4. **闭环与进化** - 每个任务形成可追踪闭环，从失败中沉淀经验

---

## 系统架构

采用 **领域驱动设计 (DDD)** 分层架构：

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SwallowLoop System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  interfaces/cli/                                                    │
│  ┌─────────────────┐                                               │
│  │  Orchestrator   │ ──────────────────────────────────────────┐   │
│  │  (主调度器)      │                                           │   │
│  └─────────────────┘                                           │   │
│           │                                                    │   │
│           ▼                                                    │   │
│  application/service/                                          │   │
│  ┌─────────────────┐    ┌─────────────────┐                    │   │
│  │  TaskService    │    │ExecutionService │                    │   │
│  │  (任务管理)      │    │  (执行管理)      │                    │   │
│  └─────────────────┘    └─────────────────┘                    │   │
│           │                      │                              │   │
│           ▼                      ▼                              │   │
│  domain/                                                        │   │
│  ┌─────────────────────────────────────────┐                    │   │
│  │ model: Task, Workspace, Comment, PR     │                    │   │
│  │ event: TaskAssigned, TaskStarted, etc.  │                    │   │
│  │ repository: TaskRepo, WorkspaceRepo     │                    │   │
│  └─────────────────────────────────────────┘                    │   │
│           │                      │                              │   │
│           ▼                      ▼                              │   │
│  infrastructure/                                                 │   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐  │   │
│  │ persistence │ │   agent     │ │source_control│ │  config   │  │   │
│  │ (JSON Repo) │ │(IFlow/Aider)│ │  (GitHub)    │ │ (Settings)│◀─┘   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 分层说明

### 1. Interfaces 层 (接口层)

**目录**: `src/swallowloop/interfaces/`

负责接收外部请求，协调应用服务完成任务。

| 文件 | 职责 |
|-----|------|
| `cli/orchestrator.py` | 主调度器，协调 TaskService 和 ExecutionService |

### 2. Application 层 (应用层)

**目录**: `src/swallowloop/application/`

负责用例编排，协调领域对象完成业务逻辑。

| 文件 | 职责 |
|-----|------|
| `service/task_service.py` | 任务生命周期管理：扫描 Issue、创建任务、状态流转 |
| `service/execution_service.py` | 任务执行管理：Worker 进程管理、结果检查 |
| `dto/issue_dto.py` | Issue 数据传输对象 |

### 3. Domain 层 (领域层)

**目录**: `src/swallowloop/domain/`

核心业务逻辑，不依赖任何外部框架。

| 目录 | 文件 | 职责 |
|-----|------|------|
| `model/` | `task.py` | Task 聚合根，状态机管理 |
| `model/` | `workspace.py` | 工作空间实体 |
| `model/` | `enums.py` | TaskState、TaskType 枚举 |
| `event/` | `task_events.py` | 领域事件定义 |
| `repository/` | `task_repository.py` | 任务仓库接口 |

**任务状态流转**:
```
new → assign → assigned → prepare → pending → start → in_progress
                                                              │
                    ┌─────────────────────────────────────────┼─────────────────┐
                    ↓                                         ↓                 ↓
                submitted ← submit                      pending ← retry    aborted ← abort
                    │                                         ↑
                    ↓                                         │
                completed ← complete                    revise
                    │
                    └──────→ pending (用户反馈)
```

### 4. Infrastructure 层 (基础设施层)

**目录**: `src/swallowloop/infrastructure/`

负责技术实现细节，如数据库、外部 API、Agent 等。

| 目录 | 文件 | 职责 |
|-----|------|------|
| `persistence/` | `json_task_repository.py` | JSON 文件任务持久化 |
| `agent/iflow/` | `iflow_agent.py` | IFlow Agent 实现 |
| `agent/aider/` | `aider_agent.py` | Aider Agent 实现 |
| `source_control/` | `github_client.py` | GitHub API 封装 |
| `config/` | `settings.py` | 配置管理 |

---

## 目录结构

```
swallowloop/
├── src/swallowloop/
│   ├── main.py                    # 主入口
│   ├── application/               # 应用层
│   │   ├── dto/                   # 数据传输对象
│   │   └── service/               # 应用服务
│   │       ├── task_service.py    # 任务服务
│   │       └── execution_service.py # 执行服务
│   ├── domain/                    # 领域层
│   │   ├── model/                 # 领域模型
│   │   ├── event/                 # 领域事件
│   │   └── repository/            # 仓库接口
│   ├── infrastructure/            # 基础设施层
│   │   ├── agent/                 # Agent 实现
│   │   ├── config/                # 配置管理
│   │   ├── persistence/           # 持久化实现
│   │   └── source_control/        # 源码控制
│   └── interfaces/                # 接口层
│       └── cli/                   # CLI 入口
├── docs/
│   ├── architecture.md            # 架构文档
│   ├── data_models.md             # 数据模型文档
│   └── vision.md                  # 项目愿景
├── .env_template                  # 配置模板
└── pyproject.toml                 # 项目配置
```

---

## 配置说明

| 环境变量 | 说明 | 必需 | 默认值 |
|---------|------|-----|--------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | 是 | - |
| `GITHUB_REPO` | 目标仓库 (owner/repo 格式) | 是 | - |
| `OPENAI_API_KEY` | LLM API Key | 是 | - |
| `OPENAI_API_BASE_URL` | LLM API 地址 | 否 | - |
| `LLM_MODEL` | Aider 使用的模型 | 否 | `claude-sonnet-4-20250514` |
| `POLL_INTERVAL` | 轮询间隔(秒) | 否 | `60` |
| `ISSUE_LABEL` | 监听的 Issue 标签 | 否 | `swallow` |
| `BASE_BRANCH` | 默认基础分支 | 否 | `main` |
| `WORKER_TIMEOUT` | Worker 超时(秒) | 否 | `600` |

---

## 外部依赖

| 依赖 | 版本 | 用途 |
|-----|------|-----|
| PyGithub | >=2.8.1 | GitHub API 操作 |
| transitions | >=0.9.3 | 状态机实现 |
| iflow-cli-sdk | >=0.1.0 | IFlow Agent SDK |
| psutil | >=6.1.0 | 进程管理 |
| python-dotenv | - | 环境变量加载 |

---

## 运行方式

```bash
# 安装依赖
uv sync

# 启动服务
uv run swallowloop

# 或
python -m swallowloop
```

---

## 扩展方向

1. **并行任务调度** - 支持多个任务同时进行
2. **巡检与技术债治理** - 定期扫描仓库生成建议任务
3. **经验/风格记忆** - 从 PR Review 中沉淀项目知识
4. **多平台支持** - GitLab / Gitea 等