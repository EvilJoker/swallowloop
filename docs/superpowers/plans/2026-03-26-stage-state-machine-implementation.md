# Stage 状态机重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将状态机逻辑从 Issue 类剥离为独立的 StageStateMachine，支持状态转换验证、钩子、并发控制

**Architecture:** 使用 transitions 库作为状态机核心，在 domain/statemachine/ 下实现独立的 StageStateMachine 类，Issue 类保留数据模型职责

**Tech Stack:** transitions>=0.9.0

---

## 文件结构

```
src/swallowloop/domain/
├── model/
│   ├── issue.py         # 修改：移除硬编码状态转换，保留数据模型
│   └── stage.py         # 不变：枚举定义
└── statemachine/        # 新增
    ├── __init__.py
    ├── stage_machine.py # 核心：StageStateMachine 类
    ├── transitions.py   # 状态转换定义表
    └── hooks.py         # LoggerHook 实现

tests/
└── test_stage_machine.py # 新增
```

---

## Task 1: 创建 statemachine 目录和基础文件

**Files:**
- Create: `src/swallowloop/domain/statemachine/__init__.py`
- Create: `src/swallowloop/domain/statemachine/transitions.py`
- Create: `src/swallowloop/domain/statemachine/hooks.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p src/swallowloop/domain/statemachine
```

- [ ] **Step 2: 创建 transitions.py**

```python
"""状态转换定义"""
from swallowloop.domain.model import Stage, StageStatus

# 状态转换表：stage -> {current_status: [allowed_next_statuses]}
STAGE_TRANSITIONS: dict[Stage, dict[StageStatus, list[StageStatus]]] = {
    Stage.BRAINSTORM: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],  # 重新触发
        StageStatus.ERROR: [StageStatus.RUNNING],     # 重试
    },
    Stage.PLAN_FORMED: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],
        StageStatus.ERROR: [StageStatus.RUNNING],
    },
    Stage.DETAILED_DESIGN: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],
        StageStatus.ERROR: [StageStatus.RUNNING],
    },
    Stage.TASK_SPLIT: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],
        StageStatus.ERROR: [StageStatus.RUNNING],
    },
    Stage.EXECUTION: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],
        StageStatus.ERROR: [StageStatus.RUNNING],
    },
    Stage.UPDATE_DOCS: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],
        StageStatus.ERROR: [StageStatus.RUNNING],
    },
    Stage.SUBMIT: {
        StageStatus.NEW: [StageStatus.RUNNING],
        StageStatus.RUNNING: [StageStatus.PENDING, StageStatus.ERROR],
        StageStatus.PENDING: [StageStatus.APPROVED, StageStatus.REJECTED],
        StageStatus.REJECTED: [StageStatus.RUNNING],
        StageStatus.ERROR: [StageStatus.RUNNING],
    },
}


def can_transition(stage: Stage, from_status: StageStatus, to_status: StageStatus) -> bool:
    """检查状态转换是否合法"""
    if stage not in STAGE_TRANSITIONS:
        return False
    allowed = STAGE_TRANSITIONS[stage].get(from_status, [])
    return to_status in allowed


def get_valid_transitions(stage: Stage, current_status: StageStatus) -> list[StageStatus]:
    """获取指定状态的所有合法转换目标"""
    return STAGE_TRANSITIONS.get(stage, {}).get(current_status, [])
```

- [ ] **Step 3: 创建 hooks.py**

```python
"""状态转换钩子"""
import logging
from dataclasses import dataclass
from swallowloop.domain.model import Stage, StageStatus

logger = logging.getLogger(__name__)


@dataclass
class TransitionEvent:
    """转换事件"""
    issue_id: str
    stage: Stage
    from_status: StageStatus
    to_status: StageStatus


class Hook:
    """钩子基类"""
    def before_transition(self, event: TransitionEvent) -> None:
        pass

    def after_transition(self, event: TransitionEvent) -> None:
        pass


class LoggerHook(Hook):
    """日志钩子 - 记录转换前后状态"""

    def before_transition(self, event: TransitionEvent) -> None:
        logger.info(
            f"[{event.issue_id}] {event.stage.value}: "
            f"{event.from_status.value} → {event.to_status.value}"
        )

    def after_transition(self, event: TransitionEvent) -> None:
        logger.debug(f"[{event.issue_id}] 转换完成")
```

- [ ] **Step 4: 创建 __init__.py**

```python
"""状态机模块"""
from .stage_machine import StageStateMachine, InvalidTransitionError, ConcurrentModificationError
from .hooks import Hook, LoggerHook, TransitionEvent
from .transitions import can_transition, get_valid_transitions

__all__ = [
    "StageStateMachine",
    "InvalidTransitionError",
    "ConcurrentModificationError",
    "Hook",
    "LoggerHook",
    "TransitionEvent",
    "can_transition",
    "get_valid_transitions",
]
```

- [ ] **Step 5: 提交**

```bash
git add src/swallowloop/domain/statemachine/
git commit -m "feat: 创建 statemachine 目录和基础文件"
```

---

## Task 2: 实现 StageStateMachine 核心类

**Files:**
- Create: `src/swallowloop/domain/statemachine/stage_machine.py`
- Modify: `src/swallowloop/domain/model/issue.py`（移除硬编码转换方法）

- [ ] **Step 1: 创建 stage_machine.py**

```python
"""StageStateMachine 核心类"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swallowloop.domain.model import Issue
    from swallowloop.domain.repository import IssueRepository
    from .hooks import Hook, TransitionEvent

from swallowloop.domain.model import Stage, StageStatus

from .transitions import can_transition, get_valid_transitions, STAGE_TRANSITIONS


class StageStateMachineError(Exception):
    """状态机基础异常"""
    pass


class InvalidTransitionError(StageStateMachineError):
    """非法状态转换"""
    pass


class ConcurrentModificationError(StageStateMachineError):
    """并发修改冲突"""
    pass


class StageStateMachine:
    """Stage 状态机"""

    def __init__(
        self,
        issue: "Issue",
        repository: "IssueRepository",
        hooks: list["Hook"] | None = None,
    ):
        self._issue = issue
        self._repo = repository
        self._hooks = hooks or []

    def _emit_before(self, event: "TransitionEvent") -> None:
        for hook in self._hooks:
            hook.before_transition(event)

    def _emit_after(self, event: "TransitionEvent") -> None:
        for hook in self._hooks:
            hook.after_transition(event)

    def _check_version(self, expected_version: int) -> None:
        """检查版本号，版本不匹配抛出异常"""
        if self._issue.version != expected_version:
            raise ConcurrentModificationError(
                f"Issue {self._issue.id} 已被其他操作修改，请重试"
            )

    def _save(self, new_version: int | None = None) -> None:
        """保存并递增版本号"""
        if new_version is not None:
            self._issue.version = new_version
        else:
            self._issue.version += 1
        self._repo.save(self._issue)

    def start(self, stage: Stage) -> bool:
        """NEW → RUNNING"""
        state = self._issue.get_stage_state(stage)
        if not can_transition(stage, state.status, StageStatus.RUNNING):
            raise InvalidTransitionError(
                f"阶段 {stage.value} 当前状态 {state.status.value} 不能转换为 running"
            )

        event = TransitionEvent(
            issue_id=str(self._issue.id),
            stage=stage,
            from_status=state.status,
            to_status=StageStatus.RUNNING,
        )
        self._emit_before(event)

        version = self._issue.version
        state.status = StageStatus.RUNNING
        state.started_at = __import__("datetime").datetime.now()
        self._issue.current_stage = stage
        self._save(version + 1)

        self._emit_after(event)
        return True

    def execute(self, stage: Stage) -> bool:
        """RUNNING → PENDING（AI 执行完成）"""
        state = self._issue.get_stage_state(stage)
        if not can_transition(stage, state.status, StageStatus.PENDING):
            raise InvalidTransitionError(
                f"阶段 {stage.value} 当前状态 {state.status.value} 不能转换为 pending"
            )

        event = TransitionEvent(
            issue_id=str(self._issue.id),
            stage=stage,
            from_status=state.status,
            to_status=StageStatus.PENDING,
        )
        self._emit_before(event)

        version = self._issue.version
        state.status = StageStatus.PENDING
        self._save(version + 1)

        self._emit_after(event)
        return True

    def approve(self, stage: Stage, comment: str = "") -> bool:
        """PENDING → APPROVED"""
        state = self._issue.get_stage_state(stage)
        if not can_transition(stage, state.status, StageStatus.APPROVED):
            raise InvalidTransitionError(
                f"阶段 {stage.value} 当前状态 {state.status.value} 不能转换为 approved"
            )

        event = TransitionEvent(
            issue_id=str(self._issue.id),
            stage=stage,
            from_status=state.status,
            to_status=StageStatus.APPROVED,
        )
        self._emit_before(event)

        version = self._issue.version
        state.status = StageStatus.APPROVED
        state.completed_at = __import__("datetime").datetime.now()
        if comment:
            from swallowloop.domain.model import ReviewComment
            state.comments.append(ReviewComment.create(stage, "approve", comment))
        self._save(version + 1)

        self._emit_after(event)
        return True

    def reject(self, stage: Stage, reason: str) -> bool:
        """PENDING → REJECTED"""
        state = self._issue.get_stage_state(stage)
        if not can_transition(stage, state.status, StageStatus.REJECTED):
            raise InvalidTransitionError(
                f"阶段 {stage.value} 当前状态 {state.status.value} 不能转换为 rejected"
            )

        event = TransitionEvent(
            issue_id=str(self._issue.id),
            stage=stage,
            from_status=state.status,
            to_status=StageStatus.REJECTED,
        )
        self._emit_before(event)

        version = self._issue.version
        state.status = StageStatus.REJECTED
        if reason:
            from swallowloop.domain.model import ReviewComment
            state.comments.append(ReviewComment.create(stage, "reject", reason))
        self._save(version + 1)

        self._emit_after(event)
        return True

    def retry(self, stage: Stage) -> bool:
        """REJECTED/ERROR → RUNNING（重新触发）"""
        state = self._issue.get_stage_state(stage)
        if state.status not in [StageStatus.REJECTED, StageStatus.ERROR]:
            raise InvalidTransitionError(
                f"阶段 {stage.value} 当前状态 {state.status.value} 不能重新触发"
            )

        event = TransitionEvent(
            issue_id=str(self._issue.id),
            stage=stage,
            from_status=state.status,
            to_status=StageStatus.RUNNING,
        )
        self._emit_before(event)

        version = self._issue.version
        state.status = StageStatus.RUNNING
        state.started_at = __import__("datetime").datetime.now()
        self._issue.current_stage = stage
        self._save(version + 1)

        self._emit_after(event)
        return True

    def advance(self, stage: Stage) -> bool:
        """APPROVED → 下一阶段 NEW（不自动触发 AI）"""
        state = self._issue.get_stage_state(stage)
        if state.status != StageStatus.APPROVED:
            raise InvalidTransitionError(
                f"阶段 {stage.value} 当前状态 {state.status.value} 不能推进到下一阶段"
            )

        stages = list(Stage)
        current_idx = stages.index(stage)
        if current_idx >= len(stages) - 1:
            # 最后一个阶段
            return True

        next_stage = stages[current_idx + 1]
        event = TransitionEvent(
            issue_id=str(self._issue.id),
            stage=stage,
            from_status=state.status,
            to_status=StageStatus.APPROVED,  # 本阶段完成
        )
        self._emit_before(event)

        # 创建下一阶段，状态为 NEW
        self._issue.create_stage(next_stage)
        self._repo.save(self._issue)

        self._emit_after(event)
        return True

    def can_trigger(self, stage: Stage) -> bool:
        """是否可触发 AI（NEW 或 REJECTED 可触发）"""
        state = self._issue.get_stage_state(stage)
        return state.status in [StageStatus.NEW, StageStatus.REJECTED, StageStatus.ERROR]

    def get_valid_transitions(self, stage: Stage) -> list[StageStatus]:
        """获取指定阶段的合法转换列表"""
        state = self._issue.get_stage_state(stage)
        return get_valid_transitions(stage, state.status)
```

- [ ] **Step 2: 修改 issue.py，添加 version 字段**

找到 `issue.py` 中 Issue 类的 `__init__` 方法，添加 `version` 字段：

```python
@dataclass
class Issue:
    id: IssueId
    title: str
    description: str
    status: IssueStatus
    current_stage: Stage
    created_at: datetime
    archived_at: datetime | None = None
    discarded_at: datetime | None = None
    delete_at: datetime | None = None
    version: int = 0  # 新增：乐观锁版本号
```

- [ ] **Step 3: 修改 issue.py，移除硬编码转换方法**

保留 `get_stage_state`, `get_latest_rejection`, `is_active` 等查询方法，移除：
- `start_stage`
- `approve_stage`
- `reject_stage`
- `create_stage`

替换为简单的数据设置方法（供状态机内部使用）：
```python
def _set_stage_status(self, stage: Stage, status: StageStatus) -> None:
    """内部方法：设置阶段状态（由状态机调用）"""
    self.stages[stage].status = status
    self.stages[stage].started_at = datetime.now()
    self.current_stage = stage

def _set_stage_completed(self, stage: Stage, status: StageStatus) -> None:
    """内部方法：设置阶段完成状态"""
    self.stages[stage].status = status
    self.stages[stage].completed_at = datetime.now()
```

- [ ] **Step 4: 提交**

```bash
git add src/swallowloop/domain/statemachine/stage_machine.py src/swallowloop/domain/model/issue.py
git commit -m "feat: 实现 StageStateMachine 核心类"
```

---

## Task 3: 更新 IssueService 使用状态机

**Files:**
- Modify: `src/swallowloop/application/service/issue_service.py`

- [ ] **Step 1: 重写 issue_service.py 使用状态机**

修改 `issue_service.py`，替换硬编码的状态转换调用为状态机：

```python
from ...domain.statemachine import StageStateMachine, LoggerHook

class IssueService:
    def __init__(self, repository: IssueRepository, executor: "ExecutorService"):
        self._repo = repository
        self._executor = executor
        self._hooks = [LoggerHook()]

    def _get_machine(self, issue: Issue) -> StageStateMachine:
        return StageStateMachine(issue, self._repo, self._hooks)

    async def create_issue(self, title: str, description: str) -> Issue:
        issue_id = IssueId(f"issue-{uuid.uuid4().hex[:8]}")
        issue = Issue(
            id=issue_id,
            title=title,
            description=description,
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        # 创建头脑风暴阶段（状态为 NEW）
        issue.create_stage(Stage.BRAINSTORM)
        self._repo.save(issue)
        logger.info(f"创建 Issue: {issue_id} - {title}，已创建头脑风暴阶段")

        # 自动触发 AI
        machine = self._get_machine(issue)
        machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
        await self._executor.execute_stage(issue, Stage.BRAINSTORM)

        return issue

    async def approve_stage(self, issue_id: str, stage: Stage, comment: str = "") -> Issue | None:
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        machine = self._get_machine(issue)
        machine.approve(stage, comment)  # → APPROVED
        machine.advance(stage)  # → 下一阶段 NEW

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 审批通过")
        return issue

    def reject_stage(self, issue_id: str, stage: Stage, reason: str) -> Issue | None:
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return None

        machine = self._get_machine(issue)
        machine.reject(stage, reason)  # → REJECTED

        logger.info(f"Issue {issue_id} 阶段 {stage.value} 已打回: {reason}")
        return issue

    async def trigger_ai(self, issue_id: str, stage: Stage) -> dict:
        issue = self._repo.get(IssueId(issue_id))
        if not issue:
            return {"status": "error", "message": "Issue not found"}

        machine = self._get_machine(issue)
        if not machine.can_trigger(stage):
            return {"status": "error", "message": f"当前状态不能触发 AI"}

        machine.start(stage)  # NEW/REJECTED → RUNNING
        return await self._executor.execute_stage(issue, stage)
```

- [ ] **Step 2: 提交**

```bash
git add src/swallowloop/application/service/issue_service.py
git commit -m "refactor: IssueService 使用状态机"
```

---

## Task 4: 编写测试用例

**Files:**
- Create: `tests/test_stage_machine.py`

- [ ] **Step 1: 编写测试用例**

```python
"""StageStateMachine 测试"""
import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.domain.repository import IssueRepository
from swallowloop.domain.statemachine import (
    StageStateMachine,
    InvalidTransitionError,
    ConcurrentModificationError,
    LoggerHook,
)


class MockRepository(IssueRepository):
    def __init__(self):
        self._issues = {}
        self._save_count = 0

    def get(self, issue_id: IssueId) -> Issue | None:
        return self._issues.get(str(issue_id))

    def save(self, issue: Issue) -> None:
        self._issues[str(issue.id)] = issue
        self._save_count += 1

    def list_all(self) -> list[Issue]:
        return list(self._issues.values())


def create_test_issue() -> Issue:
    """创建测试用 Issue"""
    issue = Issue(
        id=IssueId("test-issue"),
        title="测试",
        description="测试描述",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )
    issue.create_stage(Stage.BRAINSTORM)
    return issue


def test_new_to_running():
    """NEW → RUNNING"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine = StageStateMachine(issue, repo, [LoggerHook()])
    assert machine.start(Stage.BRAINSTORM) is True
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING


def test_running_to_pending():
    """RUNNING → PENDING"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine = StageStateMachine(issue, repo)
    machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
    assert machine.execute(Stage.BRAINSTORM) is True
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.PENDING


def test_invalid_transition():
    """非法转换应抛出异常"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine = StageStateMachine(issue, repo)
    with pytest.raises(InvalidTransitionError):
        machine.approve(Stage.BRAINSTORM, "comment")  # NEW 不能直接 APPROVE


def test_reject_and_retry():
    """REJECTED → RUNNING（重新触发）"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine = StageStateMachine(issue, repo)
    machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
    machine.execute(Stage.BRAINSTORM)  # RUNNING → PENDING
    machine.reject(Stage.BRAINSTORM, "需要修改")  # PENDING → REJECTED

    assert machine.retry(Stage.BRAINSTORM) is True
    assert issue.get_stage_state(Stage.BRAINSTORM).status == StageStatus.RUNNING


def test_advance_to_next_stage():
    """APPROVED → 下一阶段 NEW"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine = StageStateMachine(issue, repo)
    machine.start(Stage.BRAINSTORM)
    machine.execute(Stage.BRAINSTORM)
    machine.approve(Stage.BRAINSTORM, "通过")

    assert machine.advance(Stage.BRAINSTORM) is True
    assert issue.current_stage == Stage.PLAN_FORMED
    assert issue.get_stage_state(Stage.PLAN_FORMED).status == StageStatus.NEW


def test_concurrent_modification():
    """并发修改应抛出异常"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine1 = StageStateMachine(issue, repo)
    machine2 = StageStateMachine(issue, repo)

    machine1.start(Stage.BRAINSTORM)  # version: 0 → 1

    # machine2 不知道 version 已变化，应抛出异常
    with pytest.raises(ConcurrentModificationError):
        machine2.start(Stage.BRAINSTORM)  # 期望 version=0，实际=1


def test_can_trigger():
    """can_trigger 检查"""
    repo = MockRepository()
    issue = create_test_issue()
    repo.save(issue)

    machine = StageStateMachine(issue, repo)

    # NEW 可以触发
    assert machine.can_trigger(Stage.BRAINSTORM) is True

    machine.start(Stage.BRAINSTORM)  # NEW → RUNNING
    # RUNNING 不能触发
    assert machine.can_trigger(Stage.BRAINSTORM) is False
```

- [ ] **Step 2: 运行测试验证**

```bash
uv run pytest tests/test_stage_machine.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/test_stage_machine.py
git commit -m "test: 添加状态机测试用例"
```

---

## Task 5: 更新 pyproject.toml 添加 transitions 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加依赖**

在 `pyproject.toml` 的 `dependencies` 部分添加：

```toml
transitions = ">=0.9.0"
```

- [ ] **Step 2: 安装依赖**

```bash
uv sync
```

- [ ] **Step 3: 提交**

```bash
git add pyproject.toml
git commit -m "chore: 添加 transitions 依赖"
```

---

## Task 6: 运行完整测试确保无回归

- [ ] **Step 1: 运行所有测试**

```bash
uv run pytest tests/ -v
```

- [ ] **Step 2: 修复任何回归问题**

- [ ] **Step 3: 提交**

```bash
git add -A
git commit -m "fix: 修复测试回归问题"
```

---

## Task 7: 更新文档

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/data_models.md`

- [ ] **Step 1: 更新架构文档**

在 `docs/architecture.md` 中添加状态机模块说明。

- [ ] **Step 2: 更新数据模型文档**

在 `docs/data_models.md` 中添加 `version` 字段说明。

- [ ] **Step 3: 提交**

```bash
git add docs/architecture.md docs/data_models.md
git commit -m "docs: 更新文档说明状态机模块"
```
