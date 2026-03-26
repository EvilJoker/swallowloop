# SwallowLoop 架构文档

## 项目概述

**SwallowLoop · 燕子回环**：围绕代码仓库的智能维护 Agent 系统。

### 项目愿景

为程序员个人/小团队提供一个多阶段流水线协作系统：通过 7 阶段流水线（头脑风暴 → 方案成型 → 详细设计 → 任务拆分 → 执行 → 更新文档 → 提交），实现 AI 辅助开发，每个阶段由人类审批把关。

### 核心设计思想

1. **Human-in-the-loop** - 每个阶段由 AI 产出，人类审批通过后才进入下一阶段
2. **透明可控** - 所有 AI 产出都可见可修改，人类保留最终决策权
3. **闭环追溯** - 每次审批记录在案，形成完整的审核历史

---

## 系统架构

采用 **领域驱动设计 (DDD)** 分层架构：

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SwallowLoop System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  interfaces/                                                        │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │   Web API       │    │   WebSocket     │                        │
│  │   (FastAPI)     │    │   (日志推送)     │                        │
│  └─────────────────┘    └─────────────────┘                        │
│           │                      │                                  │
│           ▼                      ▼                                  │
│  application/service/                                              │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │  IssueService   │    │ ExecutorService │                        │
│  │  (生命周期管理)  │    │  (AI 执行编排)   │                        │
│  └─────────────────┘    └─────────────────┘                        │
│           │                      │                                  │
│           ▼                      ▼                                  │
│  domain/                                                            │
│  ┌─────────────────────────────────────────┐                        │
│  │ model: Issue, Stage, StageState        │                        │
│  │       TodoItem, Comment                 │                        │
│  │ repository: IssueRepository            │                        │
│  └─────────────────────────────────────────┘                        │
│           │                      │                                  │
│           ▼                      ▼                                  │
│  infrastructure/                                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│  │ persistence │ │    self_    │ │   config     │                 │
│  │ (JSON Repo) │ │   update    │ │  (Settings)  │                 │
│  └─────────────┘ └─────────────┘ └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 分层说明

### 1. Interfaces 层 (接口层)

**目录**: `src/swallowloop/interfaces/`

负责接收外部请求，提供 REST API 和 WebSocket。

| 目录 | 文件 | 职责 |
|-----|------|------|
| `web/api/` | `issues.py` | Issue REST API 路由 |
| `web/` | `app.py` | FastAPI 应用入口 |

### 2. Application 层 (应用层)

**目录**: `src/swallowloop/application/`

负责用例编排，协调领域对象完成业务逻辑。

| 文件 | 职责 |
|-----|------|
| `service/issue_service.py` | Issue 生命周期管理、状态流转 |
| `service/executor_service.py` | AI 执行编排（暂不支持 AI） |
| `dto/issue_dto.py` | Issue 数据传输对象 |

### 3. Domain 层 (领域层)

**目录**: `src/swallowloop/domain/`

核心业务逻辑，不依赖任何外部框架。

| 文件 | 职责 |
|-----|------|
| `model/issue.py` | Issue 聚合根 |
| `model/stage.py` | Stage/StageStatus/IssueStatus 枚举 |
| `model/comment.py` | Comment 值对象 |
| `repository/issue_repository.py` | Issue 仓库接口 |

### 4. Infrastructure 层 (基础设施层)

**目录**: `src/swallowloop/infrastructure/`

负责技术实现细节。

| 目录 | 文件 | 职责 |
|-----|------|------|
| `persistence/` | `json_issue_repository.py` | JSON 文件持久化（带文件锁） |
| `config/` | `settings.py` | 配置管理 |
| `self_update.py` | `self_update.py` | 自更新机制 |

---

## Issue 流水线

### 7 阶段定义

| 阶段 | 说明 | AI 产出 | 人类操作 |
|-----|------|--------|---------|
| **brainstorm** | 头脑风暴 | 多个可行方案 | 选择方案 |
| **planFormed** | 方案成型 | 整体实现思路 | 审核（通过/打回） |
| **detailedDesign** | 详细设计 | 精细化技术设计 | 审核（通过/打回） |
| **taskSplit** | 任务拆分 | TODO 列表 | 审核（通过/打回） |
| **execution** | 执行 | 代码变更 | 监控进度 |
| **updateDocs** | 更新文档 | 总结报告 | 查看 |
| **submit** | 提交 | PR | 最终审核 |

### 阶段状态

| 状态 | 说明 |
|-----|------|
| `new` | 新建（刚进入阶段，等待触发） |
| `pending` | 待审批（AI 完成，等待人类审核） |
| `approved` | 已通过 |
| `rejected` | 已打回（附带修改意见） |
| `running` | 执行中 |
| `error` | 异常 |

### 阶段流转

```
┌─────────────────────────────────────────────────────────────┐
│  单个阶段内                                                  │
│                                                             │
│   new ──► running ──► pending ──► approved              │
│                ▲         │                                  │
│                └──── rejected ◄──（用户拒绝）            │
│                          │                                │
│                          ▼（重新触发）                       │
│                      running                               │
└─────────────────────────────────────────────────────────────┘

跨阶段流转：
当前阶段 approved ──► 下一阶段 new（不自动触发）
```

---

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `ISSUE_PROJECT` | 项目名称 | `default` |
| `WEB_PORT` | Web 服务端口 | `8080` |
| `WEB_HOST` | Web 服务监听地址 | `0.0.0.0` |
| `ENABLE_SELF_UPDATE` | 是否启用自更新 | `true` |
| `SELF_UPDATE_INTERVAL` | 自更新检查间隔(秒) | `300` |

---

## 目录结构

```
swallowloop/
├── src/swallowloop/
│   ├── application/               # 应用层
│   │   ├── dto/                   # 数据传输对象
│   │   └── service/               # 应用服务
│   │       ├── issue_service.py   # Issue 服务
│   │       └── executor_service.py # 执行服务
│   ├── domain/                    # 领域层
│   │   ├── model/                # 领域模型
│   │   └── repository/           # 仓库接口
│   ├── infrastructure/            # 基础设施层
│   │   ├── config/               # 配置管理
│   │   ├── persistence/          # 持久化实现
│   │   └── self_update.py        # 自更新
│   └── interfaces/                # 接口层
│       └── web/                  # Web API
├── docs/
│   ├── architecture.md            # 架构文档
│   ├── data_models.md            # 数据模型文档
│   ├── vision.md                 # 项目愿景
│   └── test_scenarios.md         # 测试场景
├── tests/                         # 测试用例
└── pyproject.toml                 # 项目配置
```

---

## 数据文件位置

| 文件 | 路径 | 说明 |
|-----|------|------|
| Issue 数据 | `~/.swallowloop/{project}/issues.json` | Issue 持久化存储 |

---

## 外部依赖

| 依赖 | 版本 | 用途 |
|-----|------|-----|
| FastAPI | >=0.109.0 | Web 框架 |
| uvicorn | >=0.27.0 | ASGI 服务器 |
| websockets | >=12.0 | WebSocket 支持 |

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
