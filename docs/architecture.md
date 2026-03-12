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

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SwallowLoop System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │   GitHub    │───▶│   Orchestrator  │───▶│     Worker      │     │
│  │   Issues    │    │    (调度器)      │    │    (执行器)      │     │
│  └─────────────┘    └─────────────────┘    └─────────────────┘     │
│         │                   │                      │               │
│         │                   ▼                      │               │
│         │          ┌─────────────────┐             │               │
│         │          │  TaskManager    │             │               │
│         │          │  (任务持久化)    │             │               │
│         │          └─────────────────┘             │               │
│         │                   │                      │               │
│         │                   ▼                      ▼               │
│         │          ┌─────────────────────────────────┐             │
│         │          │       WorkspaceManager          │             │
│         │          │         (工作空间管理)           │             │
│         │          └─────────────────────────────────┘             │
│         │                                           │               │
│         ▼                                           ▼               │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │                     GitHub API                          │       │
│  │   (Issues, Comments, Branches, Pull Requests)           │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 模块说明

### 1. Orchestrator (调度器)

**文件**: `src/swallowloop/orchestrator.py`

**职责**:
- 扫描 GitHub Issues（带 `swallow` 标签）
- 创建任务并分配工作空间
- 启动 Worker 进程执行任务
- 监控任务状态变化
- 处理用户评论反馈
- 提交 PR 并通知

**状态流转**:
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

### 2. Worker (执行器)

**文件**: `src/swallowloop/worker.py`

**职责**:
- 克隆/更新仓库代码
- 创建/切换任务分支
- 调用 Aider 进行代码修改
- Git 提交和推送
- 创建/更新 Pull Request

**工作流程**:
```
clone/pull repo → checkout/create branch → run aider → commit → push → create PR
```

### 3. TaskManager (任务管理)

**文件**: `src/swallowloop/task_manager.py`

**职责**:
- 任务持久化存储（JSON 格式）
- 任务的 CRUD 操作
- 任务状态恢复（重启后）

### 4. WorkspaceManager (工作空间管理)

**文件**: `src/swallowloop/workspace_manager.py`

**职责**:
- 工作空间目录创建/分配
- 工作空间命名规范
- 工作空间清理

**命名规则**: `issue{issue_number}_{repo_name}_{date}`

### 5. GitHubClient (GitHub API 封装)

**文件**: `src/swallowloop/github_client.py`

**职责**:
- GitHub API 调用封装
- Issue/Comment 操作
- PR 创建/查询
- 分支管理

### 6. Models (数据模型)

**文件**: `src/swallowloop/models.py`

**职责**:
- Task 数据模型
- TaskState 状态枚举
- TaskType 类型枚举
- Workspace 数据模型
- 状态机定义

### 7. Config (配置管理)

**文件**: `src/swallowloop/config.py`

**职责**:
- 环境变量加载
- 配置验证
- 默认值管理

---

## 目录结构

```
swallowloop/
├── src/swallowloop/
│   ├── __init__.py          # 包入口
│   ├── __main__.py          # python -m 入口
│   ├── main.py              # 主入口，启动前清理旧进程
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型 + 状态机
│   ├── orchestrator.py      # 调度器
│   ├── worker.py            # 执行器
│   ├── task_manager.py      # 任务持久化
│   ├── workspace_manager.py # 工作空间管理
│   └── github_client.py     # GitHub API 封装
│
├── docs/
│   ├── architecture.md      # 架构文档（本文件）
│   └── data_models.md       # 数据模型文档
│
├── .env                     # 本地配置（不提交）
├── .env_template            # 配置模板
├── pyproject.toml           # 项目配置
└── README.md                # 项目说明
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
| aider-chat | >=0.86.0 | 代码生成 Agent |
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
