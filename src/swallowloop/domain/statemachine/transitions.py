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