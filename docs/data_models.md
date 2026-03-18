# SwallowLoop 数据模型文档

## 概述

SwallowLoop 使用状态机管理任务生命周期，所有数据持久化到 `~/.swallowloop/` 目录。

---

## 1. Task (任务模型)

### 字段定义

| 字段名 | 类型 | 说明 | 必需 |
|-------|------|------|-----|
| `id` | str | 任务唯一标识 | 是 |
| `issue_number` | int | GitHub Issue 编号 | 是 |
| `title` | str | 任务标题 | 是 |
| `description` | str | 任务描述 | 否 |
| `task_type` | TaskType | 任务类型 | 否 |
| `branch_name` | str \| None | 分支名称 | 否 |
| `repo_url` | str \| None | Git 仓库地址 | 否 |
| `labels` | list[str] | Issue 标签列表 | 否 |
| `workspace` | Workspace \| None | 关联的工作空间 | 否 |
| `pr` | PullRequest \| None | 关联的 PR | 否 |
| `comments` | list[Comment] | 用户评论列表 | 否 |
| `latest_comment` | Comment \| None | 最新评论 | 否 |
| `retry_count` | int | 重试次数 | 否 |
| `submission_count` | int | 提交次数 | 否 |
| `worker_pid` | int \| None | Worker 进程 PID | 否 |
| `started_at` | datetime \| None | 开始时间 | 否 |
| `created_at` | datetime | 创建时间 | 否 |
| `updated_at` | datetime | 更新时间 | 否 |
| `state` | str | 当前状态 | 是 |

### JSON 存储示例

```json
{
  "task_id": "task-3",
  "issue_number": 3,
  "title": "添加用户登录功能",
  "description": "请实现用户登录功能...",
  "task_type": "new_task",
  "state": "submitted",
  "branch_name": "feature_3_0318-user-login",
  "repo_url": "https://github.com/owner/repo.git",
  "labels": ["swallow", "feature"],
  "pr_number": 4,
  "pr_url": "https://github.com/owner/repo/pull/4",
  "retry_count": 0,
  "submission_count": 1,
  "comments": [],
  "created_at": "2026-03-18T10:00:00",
  "updated_at": "2026-03-18T12:30:00"
}
```

---

## 2. TaskState (任务状态)

### 状态枚举

| 状态 | 值 | 说明 |
|-----|-----|------|
| `NEW` | `new` | 新接受，等待分配工作空间 |
| `ASSIGNED` | `assigned` | 已分配工作空间 |
| `PENDING` | `pending` | 待执行，等待 Worker 启动 |
| `IN_PROGRESS` | `in_progress` | 执行中 |
| `SUBMITTED` | `submitted` | 已提交 PR |
| `COMPLETED` | `completed` | 已完成（Issue 关闭） |
| `ABORTED` | `aborted` | 异常终止 |

### 状态转换触发器

| 触发器 | 源状态 | 目标状态 | 条件 |
|-------|-------|---------|------|
| `assign` | new | assigned | - |
| `prepare` | assigned | pending | - |
| `start` | pending | in_progress | - |
| `submit` | in_progress | submitted | - |
| `complete` | submitted | completed | - |
| `retry` | in_progress | pending | retry_count < 5 |
| `abort` | any | aborted | - |
| `revise` | submitted | pending | 用户评论反馈 |

---

## 3. TaskType (任务类型)

| 类型 | 值 | 说明 |
|-----|-----|------|
| `NEW_TASK` | `new_task` | 新任务，需要 clone 仓库 |
| `REVISION` | `revision` | 修改任务，在现有分支继续工作 |

---

## 4. Workspace (工作空间模型)

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `id` | str | 工作空间 ID |
| `issue_number` | int | 关联的 Issue |
| `branch_name` | str | 分支名 |
| `path` | Path | 本地路径 |
| `pr_number` | int \| None | PR 编号 |
| `created_at` | datetime | 创建时间 |

### 命名规则

**工作空间 ID**: `{type}_{issue_number}_{date}-{slug}`

示例: `feature_3_0318-user-login`

**分支名称**: `{type}_{issue_number}_{date}-{slug}`

示例: `feature_3_0318-user-login`

---

## 5. ExecutionResult (执行结果)

Worker 执行完成后返回的结果对象。

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `success` | bool | 是否成功 |
| `message` | str | 结果消息 |
| `files_changed` | list[str] | 修改的文件列表 |
| `output` | str | 执行输出 |
| `commit_message` | str \| None | AI 生成的 commit message |

---

## 6. Settings (配置模型)

### 字段定义

| 字段名 | 类型 | 说明 | 默认值 |
|-------|------|------|--------|
| `github_token` | str | GitHub Token | - |
| `github_repo` | str | 目标仓库 | - |
| `llm_config` | LLMConfig | LLM 配置 | 默认使用 iFlow |
| `agent_type` | str | Agent 类型 | `iflow` |
| `agent_timeout` | int | Agent 超时(秒) | `1200` (20分钟) |
| `max_workers` | int | 最大并发 Worker | `5` |
| `work_dir` | Path \| None | 工作目录 | `~/.swallowloop` |
| `poll_interval` | int | 轮询间隔(秒) | `60` |
| `issue_label` | str | Issue 标签 | `swallow` |
| `base_branch` | str | 基础分支 | `main` |
| `log_level` | str | 日志级别 | `INFO` |
| `web_enabled` | bool | 启用 Web | `true` |
| `web_port` | int | Web 端口 | `8080` |
| `web_host` | str | Web 监听地址 | `0.0.0.0` |
| `enable_self_update` | bool | 启用自更新 | `true` |
| `self_update_interval` | int | 更新检查间隔(秒) | `300` |

---

## 7. LLMConfig (LLM 配置模型)

支持多种 LLM 提供商的统一配置。

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `provider` | LLMProvider | LLM 提供商 |
| `model_name` | str | 模型名称 |
| `api_key` | str \| None | API Key |
| `base_url` | str \| None | API 端点 URL |
| `extra_params` | dict | 额外参数 |

### LLMProvider (LLM 提供商枚举)

| 值 | 说明 |
|-----|------|
| `iflow` | 使用本地 iFlow CLI 默认配置 |
| `openai` | OpenAI API |
| `minimax` | MiniMax API |
| `custom` | 自定义 OpenAI 兼容 API |

### 配置方式

**方式一：使用 LLM_* 前缀环境变量**
```bash
LLM_PROVIDER=minimax
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.minimaxi.com/v1
LLM_MODEL_NAME=MiniMax-M2.5-highspeed
```

**方式二：兼容旧环境变量**
```bash
OPENAI_API_KEY=your-api-key  # 可用于 Minimax
OPENAI_API_BASE_URL=https://api.minimaxi.com/v1
LLM_MODEL=minimax/MiniMax-M2.5-highspeed
```

---

## 数据文件位置

| 文件 | 路径 | 说明 |
|-----|------|------|
| 任务数据 | `~/.swallowloop/tasks.json` | 任务持久化存储 |
| 工作空间数据 | `~/.swallowloop/workspaces.json` | 工作空间记录 |
| 工作空间目录 | `~/.swallowloop/workspaces/` | 代码仓库工作目录 |
| 代码缓存 | `~/.swallowloop/codebase/` | 代码库缓存 |
| 日志目录 | `~/.swallowloop/logs/` | 日志文件 |

---

## Worker 进程管理

### 进程信息

| 字段 | 说明 |
|-----|------|
| `worker_pid` | Worker 子进程 PID |
| `started_at` | 启动时间（用于超时检测） |

### 超时处理

- 默认超时: 2 小时
- 超时后自动终止进程
- 任务状态标记为失败，进入重试流程

---

## JSON 并发写入保护

使用 `fcntl` 文件锁保护并发写入：

1. 获取排他锁
2. 写入临时文件
3. 原子替换原文件
4. 释放锁