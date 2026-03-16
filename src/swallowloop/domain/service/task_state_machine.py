"""任务状态机服务"""

from ..model import Task, TaskState


class TaskStateMachine:
    """
    任务状态机服务
    
    验证状态转换的合法性
    """
    
    # 合法状态转换
    VALID_TRANSITIONS = {
        TaskState.NEW: {TaskState.ASSIGNED},
        TaskState.ASSIGNED: {TaskState.PENDING},
        TaskState.PENDING: {TaskState.IN_PROGRESS},
        TaskState.IN_PROGRESS: {TaskState.SUBMITTED, TaskState.PENDING, TaskState.ABORTED},
        TaskState.SUBMITTED: {TaskState.COMPLETED, TaskState.PENDING},
        TaskState.COMPLETED: set(),  # 终态
        TaskState.ABORTED: set(),    # 终态
    }
    
    @classmethod
    def can_transition(cls, from_state: TaskState, to_state: TaskState) -> bool:
        """检查状态转换是否合法"""
        valid_targets = cls.VALID_TRANSITIONS.get(from_state, set())
        return to_state in valid_targets
    
    @classmethod
    def validate_transition(cls, from_state: TaskState, to_state: TaskState) -> None:
        """验证状态转换，不合法则抛出异常"""
        if not cls.can_transition(from_state, to_state):
            raise ValueError(
                f"Invalid state transition: {from_state.value} -> {to_state.value}"
            )
