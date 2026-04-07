# Data Model: SDD 阶段流水线

**Branch**: `001-sdd-stage-migration` | **Date**: 2026-04-07

## 核心实体

### StageState (枚举)

| 状态 | 说明 |
|------|------|
| PENDING | 等待执行 |
| RUNNING | 执行中 |
| COMPLETED | 已完成 |
| FAILED | 执行失败 |
| APPROVED | 已审批通过 |
| REJECTED | 已审批打回 |
| WAITING_APPROVAL | 等待审批 |

### StageStatus

```python
class StageStatus:
    state: StageState      # 当前状态
    reason: str            # 状态原因/描述
    timestamp: datetime    # 状态变更时间戳
```

### Stage

```python
class Stage:
    name: str                          # 阶段名称（如 "specify", "clarify"）
    tasks: list[Task]                  # 阶段包含的任务列表
    status: StageStatus                # 当前状态
    stage_content: str | None          # 阶段执行结果（JSON 字符串）
    approval_state: ApprovalState      # 审批状态
    approved_at: datetime | None       # 审批时间
    approver_comments: str | None      # 审批意见

class ApprovalState(Enum):
    NOT_REQUIRED = "not_required"      # 不需要审批（环境准备阶段）
    PENDING = "pending"                # 待审批
    APPROVED = "approved"              # 已通过
    REJECTED = "rejected"              # 已打回
```

### Task

```python
class Task:
    name: str                          # 任务名称
    handler: Callable                  # 执行函数（同步或异步）
    description: str                    # 任务描述
    status: TaskStatus                 # 任务状态
    result: TaskResult | None          # 任务执行结果

class TaskStatus:
    state: TaskState                   # 任务状态
    reason: str                        # 状态原因

class TaskResult:
    success: bool                      # 是否成功
    message: str                       # 结果消息
    data: dict | None                   # 结果数据
```

### TaskResult

```python
class TaskResult:
    success: bool                      # 执行是否成功
    message: str                       # 结果描述
    data: dict | None                  # 结构化数据（用于更新 context）
```

## Pipeline 实体

### PipelineState (枚举)

| 状态 | 说明 |
|------|------|
| PENDING | 等待执行 |
| RUNNING | 执行中 |
| WAITING_APPROVAL | 等待审批 |
| COMPLETED | 全部完成 |
| FAILED | 执行失败 |

### IssuePipeline

```python
class IssuePipeline:
    _context: PipelineContext          # 流水线上下文
    _stages: list[Stage]              # 所有阶段列表
    _agent: BaseAgent | None           # Agent 引用
    _status: PipelineStatus            # 流水线状态

class PipelineContext:
    issue_id: str                      # Issue ID
    workspace_path: str                # 工作空间路径
    repo_url: str                      # 仓库 URL
    repo_name: str                     # 仓库名称
    branch: str                        # 分支名称
    thread_id: str                     # DeerFlow Thread ID
    extra: dict                        # 额外字段（issue_title, issue_description）
```

## SDD 阶段定义

| 阶段名称 | Task 类 | 指令来源 | 审批要求 |
|---------|---------|---------|---------|
| environment | EnvironmentStage 内置 Task | 环境准备 | 不需要 |
| specify | SpecifyTask | Task 内置 | 需要 |
| clarify | ClarifyTask | Task 内置 | 需要 |
| plan | PlanTask | Task 内置 | 需要 |
| checklist | ChecklistTask | Task 内置 | 需要 |
| tasks | TaskSplitTask | Task 内置 | 需要 |
| analyze | AnalyzeTask | Task 内置 | 需要 |
| implement | ExecutionTask | Task 内置 | 需要 |
| submit | SubmitTask | Task 内置 | 需要 |

## 状态转换

### 阶段状态转换

```
PENDING → RUNNING → WAITING_APPROVAL → APPROVED → (下一阶段 PENDING)
                ↘ FAILED ↗ (用户重试后 RUNNING)
                      → REJECTED → (自动重试一次，仍失败则停止)
```

### 审批流程

1. 阶段执行完成 → `WAITING_APPROVAL`
2. 用户审批：
   - 通过：`APPROVED`，进入下一阶段
   - 打回：`REJECTED`，自动重新执行
3. 重新执行后仍失败 → `FAILED`，停止流水线

## 验证规则

1. 只有 `APPROVED` 状态的阶段才能进入下一阶段
2. 打回时必须填写 `approver_comments`
3. 阶段执行超时（30 分钟）标记为 `FAILED`
4. `environment` 阶段不需要审批
5. 触发阶段时，当前阶段必须为 `APPROVED` 或 `PENDING` 状态
6. 只有 `WAITING_APPROVAL` 状态的阶段可以审批