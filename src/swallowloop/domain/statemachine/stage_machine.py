"""StageStateMachine 核心类"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swallowloop.domain.model import Issue
    from swallowloop.domain.repository import IssueRepository

from swallowloop.domain.model import Stage, StageStatus
from swallowloop.domain.statemachine.hooks import Hook, TransitionEvent

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

    def _save(self, expected_version: int, new_version: int) -> None:
        """保存并递增版本号（乐观锁）"""
        self._check_version(expected_version)
        self._issue.version = new_version
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
        self._save(version, version + 1)

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
        self._save(version, version + 1)

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
        self._save(version, version + 1)

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
        self._save(version, version + 1)

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
        self._save(version, version + 1)

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
        version = self._issue.version
        self._issue.create_stage(next_stage)
        self._save(version, version + 1)

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
