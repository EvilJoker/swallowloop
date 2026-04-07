"""Issue API 路由"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from ....application.service import IssueService, ExecutorService
from ....application.dto import issue_to_dict, build_pipeline_info
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
        from ....infrastructure.agent import DeerFlowAgent

        repository = InMemoryIssueRepository()
        deerflow_base_url = config.get("DEERFLOW_BASE_URL", DEFAULT_DEERFLOW_BASE_URL) if config else DEFAULT_DEERFLOW_BASE_URL
        agent = DeerFlowAgent(base_url=deerflow_base_url)
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
    return {"issues": [issue_to_dict(i) for i in issues]}


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
    return {"issue": issue_to_dict(issue)}


@router.post("/issues", status_code=201)
async def create_issue(request: IssueCreate):
    """创建 Issue"""
    if _issue_service is None:
        init_services()
    issue = await _issue_service.create_issue(
        title=request.title,
        description=request.description,
    )
    return {"issue": issue_to_dict(issue)}


@router.patch("/issues/{issue_id}")
async def update_issue(issue_id: str, request: IssueUpdate):
    """更新 Issue（归档/废弃）"""
    if _issue_service is None:
        init_services()
    update_data = request.model_dump(exclude_unset=True)
    issue = _issue_service.update_issue(issue_id, **update_data)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return {"issue": issue_to_dict(issue)}


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
    return {"issue": issue_to_dict(issue)}


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
    return {"issue": issue_to_dict(issue)}


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


