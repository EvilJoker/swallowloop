# SwallowLoop 数据模型文档

## 概述

SwallowLoop 使用状态机管理任务生命周期，所有数据持久化到 `~/.swallowloop/tasks.json`。

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
| `workspace_id` | str \| None | 工作空间 ID | 否 |
| `pr_number` | int \| None | PR 编号 | 否 |
| `pr_url` | str \| None | PR 链接 | 否 |
| `comments` | list[dict] | 用户评论列表 | 否 |
| `latest_comment` | str \| None | 最新评论内容 | 否 |
| `retry_count` | int | 重试次数 | 否 |
| `submission_count` | int | 提交次数 | 否 |
| `worker_pid` | int \| None | Worker 进程 PID | 否 |
| `created_at` | datetime | 创建时间 | 否 |
| `updated_at` | datetime | 更新时间 | 否 |
| `started_at` | datetime \| None | 开始时间 | 否 |
| `state` | str | 当前状态 | 是 |

### JSON 存储示例

```json
{
  "task_id": "task-3",
  "issue_number": 3,
  "title": "[SwallowLoop Test] 添加一个简单的 hello 函数",
  "description": "请在项目中创建一个 hello.py 文件...",
  "task_type": "new_task",
  "state": "submitted",
  "branch_name": "Issue3_swallowloop-test-hello",
  "repo_url": "https://github.com/EvilJoker/hubble-pad.git",
  "workspace_id": "issue3_hubble-pad_20260312",
  "pr_number": 4,
  "pr_url": "https://github.com/EvilJoker/hubble-pad/pull/4",
  "retry_count": 0,
  "submission_count": 1,
  "comments": [
    {
      "id": 123456,
      "body": "请修改函数名",
      "created_at": "2026-03-12T10:00:00Z"
    }
  ],
  "latest_comment": "请修改函数名",
  "updated_at": "2026-03-12T19:30:00"
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

### 状态流转图

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
                    ▼                                          │
┌─────┐  assign  ┌──────────┐  prepare  ┌─────────┐  start  ┌────────────┐
│ NEW │ ──────── │ ASSIGNED │ ───────── │ PENDING │ ─────── │ IN_PROGRESS │
└─────┘          └──────────┘           └─────────┘         └────────────┘
                                                          │         │
                                           ┌──────────────┤         ├──────────────┐
                                           │              │         │              │
                                           ▼              │         ▼              ▼
                                      ┌──────────┐        │   ┌──────────┐   ┌─────────┐
                                      │ PENDING  │◄───────┤   │ SUBMITTED│   │ ABORTED │
                                      └──────────┘  retry │   └──────────┘   └─────────┘
                                           ▲              │         │
                                           │              │         │
                                      ┌────┴─────┐        │         │
                                      │  revise  │────────┘         │
                                      └──────────┘                  ▼
                                                              ┌───────────┐
                                                              │ COMPLETED │
                                                              └───────────┘
```

### 状态转换触发器

| 触发器 | 源状态 | 目标状态 | 条件 |
|-------|-------|---------|------|
| `assign` | new | assigned | - |
| `prepare` | assigned | pending | - |
| `start` | pending | in_progress | - |
| `submit` | in_progress | submitted | - |
| `complete` | submitted | completed | - |
| `retry` | in_progress | pending | retry_count < max_retries |
| `abort` | in_progress | aborted | - |
| `revise` | submitted | pending | 用户评论反馈 |

---

## 3. TaskType (任务类型)

| 类型 | 值 | 说明 |
|-----|-----|------|
| `NEW_TASK` | `new_task` | 新任务，需要 clone 仓库 |
| `REVISION` | `revision` | 修改任务，在现有代码空间继续工作 |

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

**工作空间 ID**: `issue{issue_number}_{repo_name}_{date}`

示例: `issue3_hubble-pad_20260312`

**分支名称**: `Issue{issue_number}_{slug}`

示例: `Issue3_swallowloop-test-hello`

---

## 5. TaskResult (执行结果)

Worker 执行完成后返回的结果对象。

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `success` | bool | 是否成功 |
| `message` | str | 结果消息 |
| `files_changed` | list[str] | 修改的文件列表 |
| `output` | str | 执行输出 |
| `pr_url` | str \| None | PR 链接 |
| `pr_number` | int \| None | PR 编号 |

---

## 6. Config (配置模型)

### 字段定义

| 字段名 | 类型 | 说明 | 默认值 |
|-------|------|------|--------|
| `github_token` | str | GitHub Token | - |
| `github_repo` | str | 目标仓库 | - |
| `openai_api_key` | str \| None | OpenAI API Key | None |
| `openai_api_base_url` | str \| None | API Base URL | None |
| `work_dir` | Path \| None | 工作目录 | `~/.swallowloop` |
| `poll_interval` | int | 轮询间隔(秒) | 60 |
| `issue_label` | str | Issue 标签 | `swallow` |
| `base_branch` | str | 基础分支 | `main` |
| `llm_model` | str | LLM 模型 | `claude-sonnet-4-20250514` |
| `worker_timeout` | int | Worker 超时(秒) | 600 |
| `auto_test` | bool | 自动测试 | False |

---

## 数据文件位置

| 文件 | 路径 | 说明 |
|-----|------|------|
| 任务数据 | `~/.swallowloop/tasks.json` | 任务持久化存储 |
| 工作空间 | `~/.swallowloop/workspaces/` | 代码仓库工作目录 |

---

## 评论数据结构

存储在 Task 的 `comments` 字段中，排除 Bot 评论。

```python
comment = {
    "id": 123456,           # GitHub Comment ID
    "body": "请修改...",     # 评论内容
    "created_at": "2026-03-12T10:00:00Z"  # 创建时间
}
```

**用途**: Worker 收到修改任务时，可以从 `latest_comment` 获取用户最新的反馈意见。
