# SwallowLoop · 燕子回环

> 围绕你的代码仓，一圈一圈像搭建巢穴一样，维护你的项目。

## 简介

SwallowLoop 是一个智能维护 Agent 系统，为程序员个人/小团队提供常驻的代码开发助手。通过监听 GitHub Issue 并自动生成 PR 来完成代码任务。

**核心特点：**

- **Issue 驱动** - 通过 GitHub Issue 创建任务
- **7 阶段流水线** - 头脑风暴 → 方案成型 → 详细设计 → 任务拆分 → 执行 → 更新文档 → 提交
- **Human-in-the-loop** - 每个阶段人类审批，保留最终控制权
- **安全隔离** - 所有改动在独立分支，主仓只接受 PR
- **Web Dashboard** - 实时查看任务状态、日志和进度
- **完整测试** - 58 测试用例覆盖前后端

## 快速开始

### 1. 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Node.js 18+ (前端)
- GitHub Personal Access Token (需要 `repo` 权限)
- OpenAI API Key 或兼容的 LLM API

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/EvilJoker/swallowloop.git
cd swallowloop

# 安装后端依赖
uv sync

# 安装前端依赖
cd frontend && npm install && cd ..
```

### 3. 配置

```bash
# 复制配置模板
cp .env.template .env

# 编辑 .env 文件，填入你的配置
```

**必需配置：**

| 变量 | 说明 |
|-----|------|
| `REPOS` | 目标仓库 (owner/repo 格式，支持多仓库逗号分隔) |

### 4. 运行

使用 `run.sh` 脚本管理前后端服务：

```bash
# 启动全部服务（后端 + 前端）
./run.sh -all

# 单独启动后端或前端
./run.sh -backend
./run.sh -frontend

# 重启服务
./run.sh restart          # 重启全部
./run.sh restart -backend # 只重启后端

# 停止服务
./run.sh stop             # 停止全部
./run.sh stop -backend    # 只停止后端

# 查看状态
./run.sh status
```

**默认端口：**
- 后端 API: `9500`
- 前端 Dashboard: `9501`

访问 `http://localhost:9501` 查看 Dashboard。

**日志文件：**
- 后端日志：`logs/backend.log`
- 前端日志：`logs/frontend.log`

### 5. DeerFlow 部署（可选）

使用 DeerFlow Agent 时需要部署 DeerFlow：

```bash
# 克隆 DeerFlow 仓库
git clone https://github.com/YourDeerFlow/deer-flow.git
cd deer-flow

# 启动 DeerFlow Docker 容器
make docker-start

# DeerFlow 默认端口：2026
```

**配置 SwallowLoop 使用 DeerFlow：**

```bash
# 编辑 .env 文件
AGENT_TYPE=deerflow
```

## 工作流程

### Issue 7 阶段流水线

```
Issue 新建 ─▶ 头脑风暴 ─▶ 方案成型 ─▶ 详细设计 ─▶ 任务拆分 ─▶ 执行 ─▶ 更新文档 ─▶ 提交 ─▶ 归档
               │             │            │            │          │          │           │
            多个方案        整体思路      精细设计     阶段计划   执行结果   总结报告    PR
               │             │            │            │          │          │           │
               ▼             ▼            ▼            ▼          ▼          ▼           ▼
            你选择         审核         审核         审核       监控       查看        最终审核
```

### 阶段说明

| 阶段 | AI 产出 | 用户操作 |
|-----|--------|---------|
| **头脑风暴** | 多个方案 | 选择一个方案 |
| **方案成型** | 整体实现思路 | 审核（通过/打回） |
| **详细设计** | 精细化开发设计 | 审核（通过/打回） |
| **任务拆分** | 分阶段开发计划（TODO 列表） | 审核（通过/打回） |
| **执行** | 按计划执行代码 | 监控 + 手动触发 |
| **更新文档** | 更新代码文档 + 总结报告 | 查看 |
| **提交** | 提交 PR | 最终审核 |

### 阶段状态

| 状态 | 说明 |
|-----|------|
| `pending` | 待审批 |
| `approved` | 已通过 |
| `rejected` | 已打回 |
| `running` | 运行中 |
| `error` | 异常 |

## Web Dashboard

访问 `http://localhost:9501` 查看 Dashboard。

**功能：**
- 泳道图展示所有 Issue 状态
- Issue 详情面板（文档、评论历史、操作按钮）
- 执行阶段进度条和 TODO 列表
- 实时日志查看（WebSocket）

**API 端点：**

| 方法 | 端点 | 说明 |
|-----|------|------|
| GET | `/api/issues` | 获取所有 Issue |
| GET | `/api/issues/{id}` | 获取单个 Issue |
| POST | `/api/issues` | 创建 Issue |
| PATCH | `/api/issues/{id}` | 更新 Issue |
| DELETE | `/api/issues/{id}` | 删除 Issue |
| POST | `/api/issues/{id}/stages/{stage}/approve` | 审批通过 |
| POST | `/api/issues/{id}/stages/{stage}/reject` | 打回阶段 |
| POST | `/api/issues/{id}/trigger` | 手动触发 AI |
| WS | `/ws/execution/{issue_id}` | 实时日志 |

## 测试

### 运行测试

**后端测试：**
```bash
uv run pytest tests/ -v
```

**前端组件测试：**
```bash
cd frontend
npm run test:run
```

**E2E 测试：**
```bash
cd frontend
npx playwright test
```

### 测试覆盖

| 类型 | 数量 | 说明 |
|-----|------|------|
| 后端单元测试 | 25 | IssueService、API、持久化 |
| 后端集成测试 | 12 | API 端点测试 |
| 前端组件测试 | 13 | KanbanBoard、KanbanLane、IssueCard、NewIssueDialog |
| E2E 测试 | 8 | 完整用户流程 |
| **总计** | **58** | |

## 配置说明

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `REPOS` | 目标仓库 (owner/repo 格式，多仓库逗号分隔) | - |
| `LLM_PROVIDER` | LLM 提供商 (openai/minimax/custom) | `openai` |
| `LLM_API_KEY` | LLM API Key | - |
| `LLM_BASE_URL` | LLM API 端点 URL | - |
| `LLM_MODEL_NAME` | LLM 模型名称 | - |
| `AGENT_TYPE` | Agent 类型 (mock/deerflow) | `mock` |
| `AGENT_TIMEOUT` | Agent 超时(秒) | `1200` (20分钟) |
| `MAX_WORKERS` | 最大并发 Worker | `5` |
| `POLL_INTERVAL` | 轮询间隔(秒) | `60` |
| `ISSUE_LABEL` | Issue 标签 | `swallow` |
| `BASE_BRANCH` | 基础分支 | `main` |
| `WEB_ENABLED` | 启用 Web Dashboard | `true` |
| `BACKEND_PORT` | 后端 API 端口 | `9500` |
| `FRONTEND_PORT` | 前端 Dashboard 端口 | `9501` |
| `WEB_PORT` | Web 端口（旧兼容） | `8080` |
| `ENABLE_SELF_UPDATE` | 启用自更新 | `true` |

## 架构

### DDD 分层架构

```
src/swallowloop/
├── domain/                    # 领域层（核心业务逻辑）
│   ├── model/                # 聚合根、实体、值对象
│   │   ├── issue.py          # Issue 聚合根
│   │   ├── stage.py          # Stage、StageStatus 等枚举
│   │   └── comment.py        # ReviewComment
│   └── repository/           # 仓库接口定义
├── application/               # 应用层
│   ├── dto/                  # 数据传输对象
│   └── service/              # 应用服务
│       ├── issue_service.py   # Issue 生命周期管理
│       └── executor_service.py # Worker 进程管理
├── infrastructure/            # 基础设施层
│   ├── agent/               # Agent 实现 (Mock/DeerFlow)
│   ├── persistence/          # JSON 文件持久化
│   ├── source_control/      # GitHub API 封装
│   └── self_update.py       # 自更新机制
└── interfaces/               # 接口层
    ├── cli/                 # CLI 入口
    └── web/                 # Web API (FastAPI)
```

### 前端架构

```
frontend/
├── src/
│   ├── components/
│   │   ├── kanban/          # 泳道图组件
│   │   ├── issue/          # Issue 详情组件
│   │   └── layout/         # 布局组件
│   ├── pages/              # 页面
│   ├── types/              # TypeScript 类型定义
│   └── lib/                 # API 客户端
└── e2e/                    # Playwright E2E 测试
```

## 目录结构

```
swallowloop/
├── src/swallowloop/
│   ├── main.py                    # 主入口
│   ├── domain/                   # 领域层
│   ├── application/              # 应用层
│   ├── infrastructure/           # 基础设施层
│   └── interfaces/               # 接口层
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── components/           # React 组件
│   │   ├── pages/               # 页面
│   │   ├── types/               # 类型定义
│   │   └── lib/                 # 工具函数
│   ├── e2e/                     # E2E 测试
│   └── tests/                   # 组件测试
├── tests/                        # pytest 测试用例
├── docs/                         # 文档
└── pyproject.toml                # 项目配置
```

## 开发路线

- [x] Issue 7 阶段流水线
- [x] 阶段审批流程（通过/打回）
- [x] Issue 持久化存储
- [x] Web Dashboard
- [x] 执行阶段进度和 TODO 列表
- [x] 实时日志（WebSocket）
- [x] 完整测试覆盖（58 测试）
- [x] 自更新机制
- [x] 新建 Issue 功能（从头脑风暴开始）
- [x] 概览/归档页面连接后端 API
- [ ] 巡检与技术债治理
- [ ] 经验/风格记忆

## 许可证

MIT License
