# SwallowLoop 架构文档

> **文档索引**
> - [代码规范](../CODING_STANDARDS.md) - 命名、Git、测试规范
> - [术语表](../GLOSSARY.md) - 核心概念和状态机流转
> - [数据模型](./data_models.md) - 详细数据结构定义

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
│  Main Process (StageLoop)                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  while True:                                                 │   │
│  │    maintain()  # 每5秒扫描可触发的阶段                      │   │
│  │      → worker_pool.submit()                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                          │
│                           ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              InMemoryIssueRepository                         │   │
│  │   _issues: { issue-id: Issue, ... }                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           ▲                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │ IssueService   │  │ExecutorService │  │ ExecutorWorker │       │
│  │ (审批/打回)    │  │ (AI执行编排)   │  │ Pool (线程池)   │       │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘       │
│          │                    │                    │                  │
│          └────────────────────┼────────────────────┘                  │
│                               ▼                                      │
│                      StageStateMachine                               │
│                      (状态转换验证)                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Web Server Thread (后台线程)                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FastAPI (port 9500)                                       │   │
│  │  POST /issues → create_issue()                            │   │
│  │  POST /issues/{id}/approve → approve_stage()             │   │
│  │  POST /issues/{id}/reject → reject_stage()               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 层级 | 文件 | 职责 |
|------|------|------|------|
| **StageLoop** | application.service | `stage_loop.py` | 后台主循环，每5秒扫描可触发阶段 |
| **ExecutorService** | application.service | `executor_service.py` | AI 执行编排，处理 NEW→RUNNING→PENDING |
| **ExecutorWorkerPool** | infrastructure.executor | `worker_pool.py` | 线程池，管理 AI 执行并发 |
| **StageStateMachine** | domain.statemachine | `stage_machine.py` | 状态转换验证和执行 |
| **IssueService** | application.service | `issue_service.py` | Issue 生命周期，审批/打回/归档 |
| **InMemoryIssueRepository** | infrastructure.persistence | `in_memory_issue_repository.py` | 内存存储（线程安全） |

---

## 模块总览

**4 层架构**，共 **13 个子模块**：

| 层级 | 子模块 | 职责 |
|------|--------|------|
| **Domain** | model | 领域模型：Issue、Stage、Workspace、PullRequest、Comment |
| | repository | 仓库接口：IssueRepository、WorkspaceRepository |
| | statemachine | 状态机：StageStateMachine（转换规则、钩子） |
| | event | 领域事件基类 |
| **Application** | dto | 数据传输对象：IssueDTO、WorkspaceDTO |
| | service | 应用服务：IssueService、ExecutorService、StageLoop |
| **Infrastructure** | persistence | 持久化：InMemoryIssueRepository、JsonIssueRepository |
| | executor | 执行器：ExecutorWorkerPool（线程池） |
| | agent | AI Agent：BaseAgent、MockAgent |
| | config | 配置管理：Settings |
| | llm | 大模型配置：LLMConfig、LLMProvider |
| | logging | 日志：setup_logging、get_logger |
| | self_update | 自更新机制 |
| **Interfaces** | web | Web API：FastAPI 应用、REST 路由 |

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
| `new` | 新建（等待 StageLoop 触发 AI） |
| `running` | 执行中（AI 正在执行） |
| `pending` | 待审批（AI 完成，等待人类审核） |
| `approved` | 已通过 |
| `rejected` | 已打回（附带修改意见） |
| `error` | 异常 |

### 状态流转

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

StageLoop 触发（每5秒）:
  - 扫描 NEW/REJECTED/ERROR 状态
  - 检查 issue.current_stage == stage（必须是当前阶段）
  - 提交到线程池执行

跨阶段流转：
  审批通过 → advance() → 下一阶段 new（等待 StageLoop 触发）
```

---

## StageLoop 主循环

### 工作流程

```
while True:
    1. maintain()  # 扫描可触发阶段
       ├─ list_stages_by_status(NEW)
       ├─ list_stages_by_status(REJECTED)
       └─ list_stages_by_status(ERROR)

    2. 对每个可触发阶段:
       ├─ 检查 issue.status == ACTIVE
       ├─ 检查 issue.current_stage == stage
       ├─ 检查没有正在执行的任务
       └─ worker_pool.submit(issue_id, stage)

    3. sleep(5)
```

### ExecutorWorkerPool

使用 `ThreadPoolExecutor` 管理并发执行：

- `max_workers`: 最大并发数（默认 3）
- 每个任务在线程池中执行
- 内部创建新的 event loop 运行 asyncio 代码

---

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `ISSUE_PROJECT` | 项目名称 | `default` |
| `WEB_PORT` | Web 服务端口 | `9500` |
| `WEB_HOST` | Web 服务监听地址 | `0.0.0.0` |
| `AGENT_TYPE` | Agent 类型 | `mock` |
| `ENABLE_SELF_UPDATE` | 是否启用自更新 | `true` |

---

## 目录结构

```
src/swallowloop/
├── domain/           # 领域层（零依赖）
│   ├── model/        # 领域模型
│   ├── repository/   # 仓库接口
│   ├── statemachine/ # 状态机
│   └── event/        # 领域事件
│
├── application/      # 应用层（依赖 domain）
│   ├── dto/         # 数据传输对象
│   └── service/      # 应用服务
│
├── infrastructure/   # 基础设施层（依赖 domain 接口）
│   ├── persistence/  # 持久化
│   ├── executor/     # 执行器
│   ├── agent/        # AI Agent
│   ├── config/       # 配置
│   ├── llm/         # 大模型配置
│   ├── logging/      # 日志
│   └── self_update/  # 自更新
│
└── interfaces/       # 接口层（依赖 application）
    └── web/          # Web API
```

---

## 测试设计

### 分层测试策略

| 层级 | 测试范围 | 依赖处理 | 目的 |
|------|---------|---------|------|
| **module** | 单个模块提供的功能 | Mock 所有外部依赖 | 验证模块是否按契约工作 |
| **integration** | 2-3 个模块协作 | 真实模块组合 | 验证模块间接口对接 |
| **e2e** | 完整业务流程 | 真实所有层 | 验证业务闭环 |

### 组织方式

```
tests/
├── module/           # 按模块名组织，每个模块一个文件夹
│   ├── stage_machine/
│   ├── issue/
│   ├── issue_service/
│   └── ...
├── integration/      # 按协作场景组织
│   └── ...
└── e2e/            # 按业务流程组织
    └── ...
```

### 设计原则

**module 层**：
- 测试模块暴露的公开接口，不测试内部实现
- 按模块边界划分，与代码模块一一对应
- Mock 所有外部依赖，确保测试独立性

**integration 层**：
- 测试模块间的协作，如 Service + Repository
- 使用真实实现，不 Mock

**e2e 层**：
- 测试端到端业务流程，如完整 Issue 生命周期
- 通过 API 驱动，验证系统整体行为

---

## 运行方式

```bash
# 安装依赖
uv sync

# 启动服务（StageLoop 主循环 + Web 服务器）
uv run swallowloop

# 或
python -m swallowloop

# 运行测试
pytest tests/ -v
```

---

## 数据存储

当前使用 **纯内存存储**：

- `InMemoryIssueRepository`: 启动时为空，所有数据存储在内存字典中
- 适合开发测试和单实例运行
- 未来可扩展为 JSON 持久化或数据库

> 注意：原 `JsonIssueRepository` 保留但默认不使用。
