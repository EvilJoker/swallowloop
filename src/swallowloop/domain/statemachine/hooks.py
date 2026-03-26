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