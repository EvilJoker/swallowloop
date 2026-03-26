# Stage 状态机重构设计方案

## 1. 概述

将状态机逻辑从 `Issue` 类中剥离，封装为独立的 `StageStateMachine` 类，支持状态转换验证、转换钩子、并发控制。

## 2. 架构设计

```
src/swallowloop/domain/
├── model/                      # 数据模型（不变）
│   ├── issue.py
│   └── stage.py               # 枚举定义（不做修改）
└── statemachine/              # 新增：状态机模块
    ├── __init__.py
    ├── stage_machine.py       # StageStateMachine 核心类
    ├── transitions.py         # 状态转换定义表
    └── hooks.py               # 钩子实现

tests/
└── test_stage_machine.py      # 新增：状态机测试
```

## 3. 核心功能

### 3.1 状态转换验证

每个阶段的合法转换以字典形式定义：

```python
# transitions.py
STAGE_TRANSITIONS = {
    Stage.BRAINSTORM: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],  # 重新触发
        StageStatus.ERROR: [StageStatus.RUNNING],       # 重试
    },
    # ... 其他阶段类似
}
```

非法转换直接抛出 `InvalidTransitionError`。

### 3.2 转换钩子

```python
# hooks.py
class LoggerHook:
    """日志钩子 - 记录转换前后状态"""
    def before_transition(self, event: TransitionEvent) -> None:
        logger.info(f"[{event.issue_id}] {event.stage.value}: {event.from_state.value} → {event.to_state.value}")

    def after_transition(self, event: TransitionEvent) -> None:
        logger.debug(f"[{event.issue_id}] 转换完成")
```

### 3.3 并发控制

使用乐观锁机制：
- `Issue` 增加 `version` 字段（初始为 0）
- 每次转换前检查 `version`，转换后递增
- 若 `version` 不匹配，抛出 `ConcurrentModificationError`

## 4. StageStateMachine 接口

```python
class StageStateMachine:
    def __init__(self, issue: Issue, repository: IssueRepository, hooks: list[Hook] = None)

    # 状态转换
    def start(self, stage: Stage) -> bool           # NEW → RUNNING
    def execute(self, stage: Stage) -> bool         # RUNNING → PENDING（AI 执行完成）
    def approve(self, stage: Stage, comment: str) -> bool  # PENDING → APPROVED
    def reject(self, stage: Stage, reason: str) -> bool   # PENDING → REJECTED
    def advance(self, stage: Stage) -> bool         # APPROVED → 下一阶段 NEW
    def retry(self, stage: Stage) -> bool           # REJECTED/ERROR → RUNNING

    # 查询
    def can_trigger(self, stage: Stage) -> bool    # 是否可触发 AI
    def get_valid_transitions(self, stage: Stage, current_status: StageStatus) -> list[StageStatus]
```

## 5. 转换流程

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
                    ▼                                             │
NEW ──► start() ──► RUNNING ──► execute() ──► PENDING ──┬──────┤
                                                           │      │
                                              ┌────────────┴──┐   │
                                              ▼               ▼   │
                                       approve()         reject() │
                                              │               │   │
                                              ▼               ▼   │
                                         APPROVED        REJECTED│
                                              │               │   │
                                              ▼               │   │
                               advance() ──► 下一阶段 NEW ────────┘
                                              │               ▲
                                              │               │
                                              └───── retry() ──┘
```

## 6. 错误处理

| 错误类型 | 触发条件 | 处理方式 |
|---------|---------|---------|
| `InvalidTransitionError` | 非法状态转换 | 抛出异常，阻止转换 |
| `ConcurrentModificationError` | 版本号不匹配 | 抛出异常，提示重试 |
| `StageNotFoundError` | 阶段不存在 | 抛出异常 |

## 7. 测试策略

```python
# tests/test_stage_machine.py
def test_new_to_running():
    """NEW → RUNNING"""
    machine = StageStateMachine(issue, repo)
    assert machine.start(Stage.BRAINSTORM) is True
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING

def test_invalid_transition():
    """非法转换应抛出异常"""
    machine = StageStateMachine(issue, repo)
    with pytest.raises(InvalidTransitionError):
        machine.approve(Stage.BRAINSTORM, "comment")  # NEW 不能直接 APPROVE

def test_concurrent_modification():
    """并发修改应抛出异常"""
    # 模拟两个并发转换
```

## 8. Issue 类改造

移除 `issue.py` 中的硬编码状态转换方法，改为委托给 `StageStateMachine`：

```python
# issue.py - 移除 start_stage, approve_stage, reject_stage, create_stage
# 改为：
def get_state_machine(self, repository: IssueRepository) -> StageStateMachine:
    return StageStateMachine(self, repository)
```

## 9. IssueService 改造

```python
# issue_service.py
async def create_issue(self, title: str, description: str) -> Issue:
    issue = Issue(...)
    self._repo.save(issue)

    # 使用状态机自动触发 AI
    machine = issue.get_state_machine(self._repo)
    machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
    await self._executor.execute_stage(issue, Stage.BRAINSTORM)
    return issue
```

## 10. 依赖

无外部依赖，使用 Python 标准库实现。

## 11. 实施步骤

1. 创建 `domain/statemachine/` 目录和基础文件
2. 定义 `transitions.py` 状态转换表
3. 实现 `LoggerHook` 钩子
4. 实现 `StageStateMachine` 核心类
5. 更新 `Issue` 类，移除硬编码逻辑
6. 更新 `IssueService` 使用状态机
7. 编写测试用例
8. 更新文档
