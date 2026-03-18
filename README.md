# SwallowLoop · 燕子回环

> 围绕你的代码仓，一圈一圈像搭建巢穴一样，维护你的项目。

## 简介

SwallowLoop 是一个智能维护 Agent 系统，为程序员个人/小团队提供常驻的代码开发助手。只需配置仓库地址和 API Key，就能在不改变现有 Git 工作流的前提下，模拟「有一个远程实习生帮你写代码」。

**核心特点：**

- **PR 驱动** - 所有改动以 PR 形式交付，人类保留最终审批权
- **最小侵入** - 兼容现有 Git/GitHub 流程
- **安全隔离** - 所有改动在独立分支，主仓只接受 PR
- **闭环追踪** - 每个任务从规划到完成形成可追踪闭环
- **并发执行** - 支持多任务并行，可配置最大 Worker 数量
- **Web Dashboard** - 提供实时任务状态和日志查看

## 快速开始

### 1. 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 包管理器
- GitHub Personal Access Token (需要 `repo` 权限)
- IFlow CLI SDK (或 OpenAI API Key)

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

### 4. 运行

```bash
uv run swallowloop
```

启动后访问 `http://localhost:8080` 查看 Dashboard。

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

## Web Dashboard

启动后自动运行 Web 服务（默认端口 8080）：

**功能：**
- 任务列表和详情展示
- 实时日志（WebSocket）
- 统计信息

**API 端点：**
- `GET /api/tasks` - 任务列表
- `GET /api/tasks/{issue_number}` - 任务详情
- `GET /api/stats` - 统计信息
- `WS /ws/tasks/{issue_number}` - 实时日志

## 配置说明

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `GITHUB_TOKEN` | GitHub Token | - |
| `GITHUB_REPO` | 目标仓库 | - |
| `AGENT_TYPE` | Agent 类型 (iflow/aider) | `iflow` |
| `AGENT_TIMEOUT` | Agent 超时(秒) | `600` |
| `MAX_WORKERS` | 最大并发 Worker | `5` |
| `POLL_INTERVAL` | 轮询间隔(秒) | `60` |
| `ISSUE_LABEL` | Issue 标签 | `swallow` |
| `BASE_BRANCH` | 基础分支 | `main` |
| `WEB_ENABLED` | 启用 Web Dashboard | `true` |
| `WEB_PORT` | Web 端口 | `8080` |
| `ENABLE_SELF_UPDATE` | 启用自更新 | `true` |

## 架构

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub    │───▶│   Orchestrator  │───▶│   多 Worker     │
│   Issues    │    │    (调度器)      │    │   (并行执行)     │
└─────────────┘    └─────────────────┘    └─────────────────┘
                         │                        │
                         ▼                        ▼
                 ┌─────────────────┐      ┌─────────────────┐
                 │  Web Dashboard  │      │  TaskManager    │
                 │  (FastAPI)      │      │  (持久化)        │
                 └─────────────────┘      └─────────────────┘
```

**核心特性：**
- **并发控制**: 最大 Worker 数量可配置，超出的任务排队等待
- **超时检测**: Worker 2 小时超时自动终止
- **AI Commit**: 根据代码 diff 自动生成 commit message
- **自更新**: 周期检查远程版本并自动更新

详细架构文档请参阅 [docs/architecture.md](docs/architecture.md)

## 目录结构

```
swallowloop/
├── src/swallowloop/
│   ├── main.py                    # 主入口
│   ├── application/               # 应用层
│   ├── domain/                    # 领域层
│   ├── infrastructure/            # 基础设施层
│   │   ├── agent/                 # Agent 实现 (IFlow/Aider)
│   │   ├── persistence/           # 持久化
│   │   ├── source_control/        # GitHub API
│   │   └── self_update.py         # 自更新
│   └── interfaces/                # 接口层
│       ├── cli/                   # CLI 入口
│       └── web/                   # Web Dashboard
├── docs/
│   ├── architecture.md            # 架构文档
│   ├── data_models.md             # 数据模型文档
│   ├── vision.md                  # 项目愿景
│   └── test_scenarios.md          # 测试场景
├── tests/                         # 测试用例
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
- [x] 并行任务调度（最大 Worker 可配置）
- [x] 任务重试机制（最多 5 次）
- [x] AI 生成 Commit Message
- [x] Worker 超时检测
- [x] 自更新机制
- [x] Web Dashboard
- [ ] 巡检与技术债治理
- [ ] 经验/风格记忆

## 许可证

MIT License