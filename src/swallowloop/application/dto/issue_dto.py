"""Issue DTO - Issue 序列化函数"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.model import Issue, Stage

# 阶段中文标签
_STAGE_LABELS = {
    "environment": "环境准备",
    "brainstorm": "头脑风暴",
    "planFormed": "方案制定",
    "detailedDesign": "详细设计",
    "taskSplit": "任务拆分",
    "execution": "执行",
    "updateDocs": "更新文档",
    "submit": "提交",
}


def get_stage_label(stage_value: str) -> str:
    """获取阶段中文标签"""
    return _STAGE_LABELS.get(stage_value, stage_value)


def build_pipeline_info(issue: "Issue") -> dict:
    """构建 Pipeline 展示信息

    状态从 issue.pipeline.get_status() 获取
    """
    from ...domain.model import Stage

    pipeline_status = issue.pipeline.get_status()
    stages_info = []

    # 遍历 Pipeline 中的 stage，从 get_status() 获取状态
    for i, stage_obj in enumerate(issue.pipeline._stages):
        # stage_obj.name 是驼峰式 (如 'planFormed')，需要通过 value 匹配
        stage_enum = next((s for s in Stage if s.value == stage_obj.name), None)
        if stage_enum is None:
            continue

        stage_state = issue.stages.get(stage_enum)
        stage_status = pipeline_status.stages_status[i] if i < len(pipeline_status.stages_status) else None

        # 从 Pipeline Stage 获取任务信息
        tasks = []
        for j, task in enumerate(stage_obj.tasks):
            task_status = stage_status.tasks_status[j] if stage_status and j < len(stage_status.tasks_status) else None
            tasks.append({
                "name": task.name,
                "status": task_status.state.value if task_status else "pending",
            })

        # 从 issue.stages 获取时间信息
        started_at = stage_state.started_at.isoformat() if stage_state and stage_state.started_at else None
        completed_at = stage_state.completed_at.isoformat() if stage_state and stage_state.completed_at else None

        # 阶段状态从 issue.stages 获取，反映真实的审批状态
        # 而非 Pipeline 内部任务状态（Pipeline任务完成 ≠ 阶段完成，需人工审批）
        issue_stage_status = stage_state.status.value if stage_state else "new"

        stages_info.append({
            "name": stage_obj.name,
            "label": get_stage_label(stage_obj.name),
            "status": issue_stage_status,
            "startedAt": started_at,
            "completedAt": completed_at,
            "tasks": tasks,
        })

    # 计算当前阶段索引
    current_index = 0
    for i, stage in enumerate(Stage):
        if stage == issue.current_stage:
            current_index = i
            break

    return {
        "name": f"Issue-{issue.id}",
        "stages": stages_info,
        "currentStageIndex": current_index,
        "isDone": issue.running_status.value == "done",
    }


def issue_to_dict(issue: "Issue") -> dict:
    """Issue 转字典"""
    from ...domain.model import Stage, IssueRunningStatus

    # 构建 stages
    stages_dict = {}
    for stage, state in issue.stages.items():
        stages_dict[stage.value] = {
            "stage": stage.value,
            "status": state.status.value,
            "document": state.document,
            "comments": [
                {
                    "id": c.id,
                    "stage": c.stage.value,
                    "action": c.action,
                    "content": c.content,
                    "createdAt": c.created_at.isoformat(),
                }
                for c in state.comments
            ],
            "startedAt": state.started_at.isoformat() if state.started_at else None,
            "completedAt": state.completed_at.isoformat() if state.completed_at else None,
            "todoList": [
                {"id": t.id, "content": t.content, "status": t.status.value}
                for t in state.todo_list
            ] if state.todo_list else [],
        }

    return {
        "id": str(issue.id),
        "title": issue.title,
        "description": issue.description,
        "status": issue.status.value,
        "currentStage": issue.current_stage.value,
        "runningStatus": issue.running_status.value,
        "createdAt": issue.created_at.isoformat(),
        "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
        "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
        "workspace": {
            "id": issue.workspace.id if issue.workspace else None,
            "ready": issue.workspace.ready if issue.workspace else False,
            "workspace_path": issue.workspace.workspace_path if issue.workspace else "",
            "repo_url": issue.workspace.repo_url if issue.workspace else "",
            "branch": issue.workspace.branch if issue.workspace else "",
            "thread_id": issue.thread_id or "",
        } if issue.workspace else None,
        "repo_url": issue.repo_url,
        "stages": stages_dict,
        "pipeline": build_pipeline_info(issue),
    }


# ============ 以下是原有的 DTO 类 ============

@dataclass
class IssueDTO:
    """Issue 数据传输对象"""
    number: int
    title: str
    body: str
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkspaceDTO:
    """工作空间数据传输对象"""
    id: str
    issue_number: int
    branch_name: str
    path: Path
    pr_number: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
