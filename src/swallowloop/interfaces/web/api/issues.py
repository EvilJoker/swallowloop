"""Issue API 路由"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from ....application.service import IssueService, ExecutorService
from ....domain.model import Stage, IssueStatus
from ....infrastructure.persistence import JsonIssueRepository

router = APIRouter()

# 全局服务实例（简化处理，实际应该用依赖注入）
_issue_service: IssueService = None
_executor_service: ExecutorService = None


def init_services():
    """初始化服务实例"""
    global _issue_service, _executor_service
    repository = JsonIssueRepository(project="default")
    _executor_service = ExecutorService(repository=repository)
    _issue_service = IssueService(repository=repository, executor=_executor_service)


class IssueCreate(BaseModel):
    title: str
    description: str = ""


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class StageApprove(BaseModel):
    comment: str = ""


class StageReject(BaseModel):
    reason: str


class TriggerRequest(BaseModel):
    stage: str


@router.get("/issues")
async def list_issues():
    """获取所有 Issue"""
    if _issue_service is None:
        init_services()
    issues = _issue_service.list_issues()
    return {"issues": [_issue_to_dict(i) for i in issues]}


@router.get("/issues/{issue_id}")
async def get_issue(issue_id: str):
    """获取单个 Issue"""
    if _issue_service is None:
        init_services()
    issue = _issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": _issue_to_dict(issue)}


@router.post("/issues")
async def create_issue(request: IssueCreate):
    """创建 Issue"""
    if _issue_service is None:
        init_services()
    issue = _issue_service.create_issue(
        title=request.title,
        description=request.description,
    )
    return {"issue": _issue_to_dict(issue)}, 201


@router.patch("/issues/{issue_id}")
async def update_issue(issue_id: str, request: IssueUpdate):
    """更新 Issue（归档/废弃）"""
    if _issue_service is None:
        init_services()
    update_data = request.model_dump(exclude_unset=True)
    issue = _issue_service.update_issue(issue_id, **update_data)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": _issue_to_dict(issue)}


@router.delete("/issues/{issue_id}")
async def delete_issue(issue_id: str):
    """删除 Issue"""
    if _issue_service is None:
        init_services()
    success = _issue_service.delete_issue(issue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found")
    return None


@router.post("/issues/{issue_id}/stages/{stage}/approve")
async def approve_stage(issue_id: str, stage: str, request: Request):
    """审批通过阶段"""
    if _issue_service is None:
        init_services()
    body = await request.json()
    comment = body.get("comment", "")
    issue = await _issue_service.approve_stage(issue_id, Stage(stage), comment)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": _issue_to_dict(issue)}


@router.post("/issues/{issue_id}/stages/{stage}/reject")
async def reject_stage(issue_id: str, stage: str, request: Request):
    """打回阶段"""
    if _issue_service is None:
        init_services()
    body = await request.json()
    reason = body.get("reason", "")
    issue = _issue_service.reject_stage(issue_id, Stage(stage), reason)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": _issue_to_dict(issue)}


@router.post("/issues/{issue_id}/trigger")
async def trigger_issue(issue_id: str, request: Request):
    """手动触发 AI 执行"""
    if _issue_service is None:
        init_services()
    body = await request.json()
    stage = body.get("stage")
    if not stage:
        raise HTTPException(status_code=400, detail="stage is required")
    result = await _issue_service.trigger_ai(issue_id, Stage(stage))
    return result


def _issue_to_dict(issue) -> dict:
    """Issue 转字典"""
    return {
        "id": str(issue.id),
        "title": issue.title,
        "description": issue.description,
        "status": issue.status.value,
        "currentStage": issue.current_stage.value,
        "createdAt": issue.created_at.isoformat(),
        "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
        "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
        "stages": {
            stage.value: _stage_to_dict(stage.value, state)
            for stage, state in issue.stages.items()
        },
    }


def _stage_to_dict(stage_name: str, state) -> dict:
    """StageState 转字典"""
    return {
        "stage": stage_name,
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
            for t in (state.todo_list or [])
        ],
        "progress": state.progress,
        "executionState": state.execution_state.value if state.execution_state else None,
    }
