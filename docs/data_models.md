# SwallowLoop 数据模型文档

## 概述

SwallowLoop 使用 Issue 流水线管理任务，所有数据持久化到 `~/.swallowloop/{project}/issues.json`。

---

## 1. Issue (聚合根)

### 字段定义

| 字段名 | 类型 | 说明 | 必需 |
|-------|------|------|-----|
| `id` | str | Issue 唯一标识 | 是 |
| `title` | str | Issue 标题 | 是 |
| `description` | str | Issue 描述 | 是 |
| `status` | IssueStatus | Issue 状态 | 是 |
| `current_stage` | Stage | 当前所处阶段 | 是 |
| `created_at` | datetime | 创建时间 | 是 |
| `archived_at` | datetime \| None | 归档时间 | 否 |
| `discarded_at` | datetime \| None | 废弃时间 | 否 |
| `delete_at` | datetime \| None | 删除时间（废弃后+3天） | 否 |
| `stages` | dict[Stage, StageState] | 各阶段状态 | 是 |

### JSON 存储示例

```json
{
  "id": "issue-abc12345",
  "title": "实现用户登录功能",
  "description": "需要实现完整的用户登录注册流程",
  "status": "active",
  "currentStage": "execution",
  "createdAt": "2026-03-18T10:00:00",
  "archivedAt": null,
  "discardedAt": null,
  "deleteAt": null,
  "stages": {
    "brainstorm": {
      "stage": "brainstorm",
      "status": "approved",
      "document": "# 方案一：使用 JWT\n\n## 核心思路...",
      "comments": [
        {
          "id": "comment-001",
          "stage": "brainstorm",
          "action": "approve",
          "content": "选择方案一",
          "createdAt": "2026-03-18T11:00:00"
        }
      ],
      "startedAt": "2026-03-18T10:00:00",
      "completedAt": "2026-03-18T11:00:00",
      "todoList": null,
      "progress": null,
      "executionState": null
    },
    "planFormed": {
      "stage": "planFormed",
      "status": "approved",
      "document": "# 实现计划\n\n## 整体思路...",
      "comments": [],
      "startedAt": "2026-03-18T11:00:00",
      "completedAt": "2026-03-18T12:00:00",
      "todoList": null,
      "progress": null,
      "executionState": null
    },
    "execution": {
      "stage": "execution",
      "status": "running",
      "document": "",
      "comments": [],
      "startedAt": "2026-03-18T12:00:00",
      "completedAt": null,
      "todoList": [
        {"id": "todo-1", "content": "创建用户模型", "status": "completed"},
        {"id": "todo-2", "content": "实现登录 API", "status": "in_progress"},
        {"id": "todo-3", "content": "添加单元测试", "status": "pending"}
      ],
      "progress": 33,
      "executionState": "running"
    }
  }
}
```

---

## 2. Stage (阶段枚举)

### 阶段值

| 阶段 | 值 | 说明 |
|-----|-----|------|
| `BRAINSTORM` | `brainstorm` | 头脑风暴 |
| `PLAN_FORMED` | `planFormed` | 方案成型 |
| `DETAILED_DESIGN` | `detailedDesign` | 详细设计 |
| `TASK_SPLIT` | `taskSplit` | 任务拆分 |
| `EXECUTION` | `execution` | 执行 |
| `UPDATE_DOCS` | `updateDocs` | 更新文档 |
| `SUBMIT` | `submit` | 提交 |

---

## 3. StageStatus (阶段状态枚举)

| 状态 | 值 | 说明 |
|-----|-----|------|
| `NEW` | `new` | 新建（等待触发） |
| `RUNNING` | `running` | 执行中 |
| `PENDING` | `pending` | 待审批 |
| `APPROVED` | `approved` | 已通过 |
| `REJECTED` | `rejected` | 已打回 |
| `ERROR` | `error` | 异常 |

---

## 4. IssueStatus (Issue 状态枚举)

| 状态 | 值 | 说明 |
|-----|-----|------|
| `ACTIVE` | `active` | 活跃 |
| `ARCHIVED` | `archived` | 已归档 |
| `DISCARDED` | `discarded` | 已废弃 |

---

## 5. StageState (阶段状态)

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `stage` | Stage | 阶段 |
| `status` | StageStatus | 状态 |
| `document` | str | Markdown 文档内容 |
| `comments` | list[Comment] | 审核意见列表 |
| `started_at` | datetime \| None | 开始时间 |
| `completed_at` | datetime \| None | 完成时间 |
| `todo_list` | list[TodoItem] \| None | TODO 列表（执行阶段） |
| `progress` | int \| None | 进度百分比（执行阶段） |
| `execution_state` | ExecutionState \| None | 执行子状态 |

---

## 6. TodoItem (TODO 项)

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `id` | str | 唯一标识 |
| `content` | str | 内容 |
| `status` | TodoStatus | 状态 |

### TodoStatus (TODO 状态枚举)

| 状态 | 值 | 说明 |
|-----|-----|------|
| `PENDING` | `pending` | 待执行 |
| `IN_PROGRESS` | `in_progress` | 执行中 |
| `COMPLETED` | `completed` | 已完成 |
| `FAILED` | `failed` | 失败 |

---

## 7. ExecutionState (执行状态枚举)

| 状态 | 值 | 说明 |
|-----|-----|------|
| `PENDING` | `pending` | 待执行 |
| `RUNNING` | `running` | 执行中 |
| `PAUSED` | `paused` | 暂停 |
| `SUCCESS` | `success` | 成功 |
| `FAILED` | `failed` | 失败 |

---

## 8. Comment (评论/审核意见)

### 字段定义

| 字段名 | 类型 | 说明 |
|-------|------|------|
| `id` | str | 唯一标识 |
| `stage` | Stage | 所属阶段 |
| `action` | str | 操作类型（`approve`/`reject`） |
| `content` | str | 内容 |
| `created_at` | datetime | 创建时间 |

---

## 9. Settings (配置模型)

### 字段定义

| 字段名 | 类型 | 说明 | 默认值 |
|-------|------|------|--------|
| `issue_project` | str | 项目名称 | `default` |
| `log_level` | str | 日志级别 | `INFO` |
| `web_enabled` | bool | 启用 Web | `true` |
| `web_port` | int | Web 端口 | `8080` |
| `web_host` | str | Web 监听地址 | `0.0.0.0` |
| `enable_self_update` | bool | 启用自更新 | `true` |
| `self_update_interval` | int | 更新检查间隔(秒) | `300` |

---

## 数据文件位置

| 文件 | 路径 | 说明 |
|-----|------|------|
| Issue 数据 | `~/.swallowloop/{project}/issues.json` | Issue 持久化存储 |

---

## JSON 并发写入保护

使用 `fcntl` 文件锁保护并发写入：

1. 获取排他锁
2. 写入临时文件
3. 原子替换原文件
4. 释放锁
