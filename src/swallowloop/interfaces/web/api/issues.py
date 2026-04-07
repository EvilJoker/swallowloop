"""Issue API 路由"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from ....application.service import IssueService, ExecutorService
from ....domain.model import Stage, IssueStatus, IssueRunningStatus
from ....infrastructure.persistence import InMemoryIssueRepository
from ....infrastructure.constants import DEFAULT_DEERFLOW_BASE_URL

router = APIRouter()

# 全局服务实例（简化处理，实际应该用依赖注入）
_issue_service: IssueService = None
_executor_service: ExecutorService = None


def init_services():
    """初始化服务实例（从注册表获取共享实例）"""
    import os
    from ....infrastructure.instance_registry import get_instance

    global _issue_service, _executor_service

    # 优先从注册表获取共享实例
    repository = get_instance("repository")
    executor = get_instance("executor")
    ws_manager = get_instance("ws_manager")
    agent = get_instance("agent")
    config = get_instance("config")

    if repository is not None and executor is not None:
        # 使用共享实例
        _executor_service = executor
        _issue_service = IssueService(
            repository=repository,
            executor=_executor_service,
            agent=agent,
            config=config,
            ws_manager=ws_manager
        )
    else:
        # 注册表没有实例，创建新的（仅用于独立运行）
        from ....infrastructure.agent import MockAgent, DeerFlowAgent

        repository = InMemoryIssueRepository()
        agent_type = config.get("AGENT_TYPE", "mock") if config else "mock"
        deerflow_base_url = config.get("DEERFLOW_BASE_URL", DEFAULT_DEERFLOW_BASE_URL) if config else DEFAULT_DEERFLOW_BASE_URL
        if agent_type == "deerflow":
            agent = DeerFlowAgent(base_url=deerflow_base_url)
        else:
            agent = MockAgent(delay_seconds=5.0)
        _executor_service = ExecutorService(repository=repository, agent=agent, agent_type=agent_type)
        _issue_service = IssueService(repository=repository, executor=_executor_service, agent=agent)


class IssueCreate(BaseModel):
    title: str
    description: str = ""


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    runningStatus: Optional[str] = None


class StageApprove(BaseModel):
    comment: str = ""


class StageReject(BaseModel):
    reason: str


class TriggerRequest(BaseModel):
    stage: str


class RepositoryResponse(BaseModel):
    """代码仓库响应"""
    name: str
    url: str
    branch: str
    description: str


@router.get("/issues")
async def list_issues():
    """获取所有 Issue"""
    if _issue_service is None:
        init_services()
    issues = _issue_service.list_issues()
    return {"issues": [_issue_to_dict(i) for i in issues]}


@router.get("/repository", response_model=RepositoryResponse)
async def get_repository():
    """获取代码仓库配置"""
    from ....infrastructure.instance_registry import get_instance
    config = get_instance("config")
    if config:
        repo_config = config.get_repository()
        return RepositoryResponse(**repo_config)
    return RepositoryResponse(name="", url="", branch="main", description="")


@router.get("/issues/{issue_id}")
async def get_issue(issue_id: str):
    """获取单个 Issue"""
    if _issue_service is None:
        init_services()
    issue = _issue_service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": _issue_to_dict(issue)}


@router.post("/issues", status_code=201)
async def create_issue(request: IssueCreate):
    """创建 Issue"""
    if _issue_service is None:
        init_services()
    issue = await _issue_service.create_issue(
        title=request.title,
        description=request.description,
    )
    return {"issue": _issue_to_dict(issue)}


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
    """删除 Issue（硬删除）"""
    if _issue_service is None:
        init_services()
    success = await _issue_service.delete_issue(issue_id)
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
    issue = await _issue_service.reject_stage(issue_id, Stage(stage), reason)
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
        "runningStatus": issue.running_status.value,
        "workspace": {
            "id": issue.workspace.id if issue.workspace else None,
            "ready": issue.workspace.ready if issue.workspace else False,
            "workspace_path": issue.workspace.workspace_path if issue.workspace else "",
            "repo_url": issue.workspace.repo_url if issue.workspace else "",
            "branch": issue.workspace.branch if issue.workspace else "",
            "thread_id": issue.thread_id or "",
        } if issue.workspace else None,
        "repo_url": issue.repo_url,
        "stages": {
            stage.value: _stage_to_dict(stage.value, state)
            for stage, state in issue.stages.items()
        },
        "pipeline": _build_pipeline_info(issue),
    }


def _build_pipeline_info(issue) -> dict:
    """构建 Pipeline 展示信息"""
    stages_info = []
    for stage in Stage:
        state = issue.stages.get(stage)
        if state:
            # 从 todo_list 构建任务列表
            tasks = []
            if state.todo_list:
                for todo in state.todo_list:
                    tasks.append({
                        "name": todo.content,
                        "status": todo.status.value,
                    })
            stages_info.append({
                "name": stage.value,
                "label": _get_stage_label(stage),
                "status": state.status.value,
                "startedAt": state.started_at.isoformat() if state.started_at else None,
                "completedAt": state.completed_at.isoformat() if state.completed_at else None,
                "tasks": tasks,  # 始终返回列表，即使为空
            })

    # 计算当前阶段索引
    current_index = 0
    for i, stage in enumerate(Stage):
        if stage == issue.current_stage:
            current_index = i
            break

    return {
        "name": f"Issue-{issue.id.value}",
        "stages": stages_info,
        "currentStageIndex": current_index,
        "isDone": issue.running_status == IssueRunningStatus.DONE,
    }


def _get_stage_label(stage) -> str:
    """获取阶段中文标签"""
    labels = {
        Stage.ENVIRONMENT: "环境准备",
        Stage.BRAINSTORM: "头脑风暴",
        Stage.PLAN_FORMED: "方案制定",
        Stage.DETAILED_DESIGN: "详细设计",
        Stage.TASK_SPLIT: "任务拆分",
        Stage.EXECUTION: "执行",
        Stage.UPDATE_DOCS: "更新文档",
        Stage.SUBMIT: "提交",
    }
    return labels.get(stage, stage.value)


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
