"""枚举定义"""

from enum import Enum


class TaskState(Enum):
    """任务状态"""
    NEW = "new"                       # 新接受
    ASSIGNED = "assigned"             # 已分配（工作空间已分配）
    PENDING = "pending"               # 待执行（等待Worker启动）
    IN_PROGRESS = "in_progress"       # 执行中
    SUBMITTED = "submitted"           # 已提交（PR已创建）
    COMPLETED = "completed"           # 已完成（Issue已关闭）
    ABORTED = "aborted"               # 异常终止


class TaskType(Enum):
    """任务类型"""
    NEW_TASK = "new_task"             # 新任务，需要 clone
    REVISION = "revision"             # 修改任务，在现有代码空间继续工作
