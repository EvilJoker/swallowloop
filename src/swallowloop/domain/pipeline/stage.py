"""Stage - Pipeline 中的阶段，包含多个 Task"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable
from .task import Task, TaskResult, TaskStatus


class StageState(Enum):
    """Stage 执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalState(Enum):
    """审批状态枚举"""
    NOT_REQUIRED = "not_required"  # 不需要审批（如环境准备阶段）
    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已打回


@dataclass
class StageStatus:
    """Stage 状态对象"""
    state: StageState = StageState.PENDING
    reason: str = ""
    extra: dict = field(default_factory=dict)
    tasks_status: list[TaskStatus] = field(default_factory=list)  # 包含多个 TaskStatus
    current_task: str = ""  # 当前执行的 Task 名称

    def __str__(self) -> str:
        if self.reason:
            return f"{self.state.value.upper()} - {self.reason}"
        return self.state.value.upper()

    def is_pending(self) -> bool:
        return self.state == StageState.PENDING

    def is_running(self) -> bool:
        return self.state == StageState.RUNNING

    def is_waiting_approval(self) -> bool:
        return self.state == StageState.WAITING_APPROVAL

    def is_approved(self) -> bool:
        return self.state == StageState.APPROVED

    def is_rejected(self) -> bool:
        return self.state == StageState.REJECTED

    def is_completed(self) -> bool:
        return self.state == StageState.COMPLETED

    def is_failed(self) -> bool:
        return self.state == StageState.FAILED


class Stage:
    """Stage 是 Pipeline 中的一个阶段，包含多个 Task"""

    def __init__(
        self,
        name: str,
        tasks: list[Task] = None,
        description: str = "",
        requires_approval: bool = True,
    ):
        """
        Args:
            name: Stage 名称
            tasks: Task 列表
            description: Stage 描述
            requires_approval: 是否需要人类审批（环境准备阶段不需要）
        """
        self.name = name
        self.tasks = tasks or []
        self.description = description
        self.requires_approval = requires_approval
        self._status = StageStatus()
        self._last_result: TaskResult | None = None
        # 审批相关字段
        self._approval_state: ApprovalState = (
            ApprovalState.NOT_REQUIRED if not requires_approval else ApprovalState.PENDING
        )
        self._approved_at: datetime | None = None
        self._approver_comments: str | None = None

    @property
    def approval_state(self) -> ApprovalState:
        """获取审批状态"""
        return self._approval_state

    @property
    def approved_at(self) -> datetime | None:
        """获取审批时间"""
        return self._approved_at

    @property
    def approver_comments(self) -> str | None:
        """获取审批意见"""
        return self._approver_comments

    def approve(self, comments: str = "") -> None:
        """审批通过

        Args:
            comments: 审批意见
        """
        self._approval_state = ApprovalState.APPROVED
        self._approved_at = datetime.now()
        self._approver_comments = comments
        self._status.state = StageState.APPROVED
        self._status.reason = "已审批通过"

    def reject(self, comments: str) -> None:
        """审批打回

        Args:
            comments: 审批意见（必填）
        Raises:
            ValueError: 如果 comments 为空
        """
        if not comments:
            raise ValueError("打回时必须填写审批意见")
        self._approval_state = ApprovalState.REJECTED
        self._approved_at = datetime.now()
        self._approver_comments = comments
        self._status.state = StageState.REJECTED
        self._status.reason = f"已打回: {comments}"

    def set_waiting_approval(self, reason: str = "等待审批") -> None:
        """设置阶段为等待审批状态

        Args:
            reason: 状态描述
        """
        self._approval_state = ApprovalState.PENDING
        self._status.state = StageState.WAITING_APPROVAL
        self._status.reason = reason

    @property
    def status(self) -> StageStatus:
        """获取当前状态"""
        return self._status

    def get_status(self) -> StageStatus:
        """获取当前状态（兼容方法）"""
        return self._status

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """顺序执行所有 Task，如果某个 Task 返回失败则停止

        Args:
            context: 执行上下文

        Returns:
            (context, TaskResult) - TaskResult.success=True 表示全部成功，False 表示失败
        """
        tasks_status = []  # 收集所有 TaskStatus
        self._status = StageStatus(state=StageState.RUNNING, reason="执行中", tasks_status=tasks_status)

        result = context
        for task in self.tasks:
            # 更新当前执行的 Task
            self._status.current_task = task.name
            result, task_result = task.execute(result)
            self._last_result = task_result
            # 收集 TaskStatus
            tasks_status.append(task.status)
            if not task_result.success:
                # Task 执行失败，停止执行
                self._status = StageStatus(
                    state=StageState.FAILED,
                    reason=task_result.message,
                    extra={"failed_task": task.name},
                    tasks_status=tasks_status,
                    current_task=task.name
                )
                return result, task_result
        # 所有 Task 都成功
        self._status = StageStatus(
            state=StageState.COMPLETED,
            reason="执行完成",
            tasks_status=tasks_status,
            current_task=""
        )
        return result, TaskResult(success=True, message=f"Stage '{self.name}' 执行完成")

    def add_task(self, task: Task) -> None:
        """添加 Task"""
        self.tasks.append(task)

    @property
    def last_result(self) -> TaskResult | None:
        """获取最后一个 Task 的执行结果"""
        return self._last_result

    def __repr__(self) -> str:
        return f"Stage(name={self.name!r}, status={self._status})"
