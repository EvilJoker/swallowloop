# SwallowLoop · 燕子回环

> 围绕你的代码仓，一圈一圈像搭建巢穴一样，维护你的项目。

## 简介

SwallowLoop 是一个智能维护 Agent 系统，为程序员个人/小团队提供常驻的代码开发助手。只需配置仓库地址和 API Key，就能在不改变现有 Git 工作流的前提下，模拟「有一个远程实习生帮你写代码」。

**核心特点：**

- **PR 驱动** - 所有改动以 PR 形式交付，人类保留最终审批权
- **最小侵入** - 兼容现有 Git/GitHub 流程
- **安全隔离** - 所有改动在独立分支，主仓只接受 PR
- **闭环追踪** - 每个任务从规划到完成形成可追踪闭环

## 快速开始

### 1. 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 包管理器
- GitHub Personal Access Token (需要 `repo` 权限)
- LLM API Key (OpenAI / Minimax 等)

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/EvilJoker/swallowloop.git
cd swallowloop

# 安装依赖
uv sync
```

### 3. 配置

```bash
# 复制配置模板
cp .env_template .env

# 编辑 .env 文件，填入你的配置
```

**必需配置：**

| 变量 | 说明 |
|-----|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token |
| `GITHUB_REPO` | 目标仓库 (owner/repo 格式) |
| `OPENAI_API_KEY` | LLM API Key |
| `LLM_MODEL` | 模型名称 |

### 4. 运行

```bash
uv run swallowloop
```

## 使用方式

### 创建任务

在目标仓库创建 GitHub Issue，添加 `swallow` 标签：

```
标题: 添加用户登录功能
正文: 请实现用户登录功能，包括：
- 登录表单
- 密码验证
- Session 管理
```

### 工作流程

```
Issue 创建 → SwallowLoop 检测 → 代码生成 → PR 提交 → 人工审批
                                              ↓
                            用户评论反馈 → 代码修改 → PR 更新
```

### 任务状态

| 状态 | 说明 |
|-----|------|
| `new` | 新接受，等待分配工作空间 |
| `assigned` | 已分配工作空间 |
| `pending` | 待执行（新任务或重试） |
| `in_progress` | 执行中 |
| `submitted` | 已提交 PR |
| `completed` | 已完成（PR 已合并） |
| `aborted` | 异常终止（Issue 关闭或重试失败） |

### 重试机制

任务执行失败时自动重试，最多 5 次。重试后状态变为 `pending`，下次轮询时重新执行。

## 配置说明

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `GITHUB_TOKEN` | GitHub Token | - |
| `GITHUB_REPO` | 目标仓库 | - |
| `OPENAI_API_KEY` | LLM API Key | - |
| `OPENAI_API_BASE_URL` | API 地址 | - |
| `LLM_MODEL` | 模型名称 | `claude-sonnet-4-20250514` |
| `POLL_INTERVAL` | 轮询间隔(秒) | `60` |
| `ISSUE_LABEL` | Issue 标签 | `swallow` |
| `BASE_BRANCH` | 基础分支 | `main` |
| `WORKER_TIMEOUT` | Worker 超时(秒) | `600` |

### Minimax 配置示例

```env
OPENAI_API_KEY=your_minimax_api_key
OPENAI_API_BASE_URL=https://api.minimaxi.com/v1
LLM_MODEL=openai/MiniMax-M2.5-highspeed
```

### OpenAI 配置示例

```env
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4o
```

## 架构

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub    │───▶│   Orchestrator  │───▶│   多 Worker     │
│   Issues    │    │    (调度器)      │    │   (并行执行)     │
└─────────────┘    └─────────────────┘    └─────────────────┘
                         │
                         ▼
                 ┌─────────────────┐
                 │  TaskManager    │
                 │  (任务持久化)    │
                 └─────────────────┘
```

**并行执行**: 支持多任务同时执行。通过多 Worker 进程 + iFlow 多 Session 实现，每个任务独立工作空间。

详细架构文档请参阅 [docs/architecture.md](docs/architecture.md)

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
│   │   │   ├── task.py            # 任务聚合根
│   │   │   ├── workspace.py       # 工作空间
│   │   │   └── enums.py           # 枚举定义
│   │   ├── event/                 # 领域事件
│   │   └── repository/            # 仓库接口
│   ├── infrastructure/            # 基础设施层
│   │   ├── agent/                 # Agent 实现
│   │   │   ├── aider/             # Aider Agent
│   │   │   └── iflow/             # IFlow Agent
│   │   ├── config/                # 配置管理
│   │   ├── persistence/           # 持久化实现
│   │   └── source_control/        # 源码控制
│   │       └── github/            # GitHub API
│   └── interfaces/                # 接口层
│       └── cli/                   # CLI 入口
│           └── orchestrator.py    # 主调度器
├── docs/
│   ├── architecture.md            # 架构文档
│   ├── data_models.md             # 数据模型文档
│   └── vision.md                  # 项目愿景
├── .env_template                  # 配置模板
└── pyproject.toml                 # 项目配置
```

## 开发路线

- [x] Issue 监听与任务创建
- [x] 任务状态机管理
- [x] 工作空间隔离与分支管理
- [x] IFlow Agent 集成
- [x] 自动创建 PR
- [x] 用户评论触发修改
- [x] 任务持久化存储
- [x] 并行任务调度
- [x] 任务重试机制（最多 5 次）
- [ ] 巡检与技术债治理
- [ ] 经验/风格记忆
- [ ] Web 前端面板

## 许可证

MIT License
