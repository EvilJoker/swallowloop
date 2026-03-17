"""Web API 路由"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from ...domain.model import TaskState


router = APIRouter()


def get_task_repo(request: Request):
    """获取任务仓库"""
    return request.app.state.task_repo_factory()


def get_workspace_repo(request: Request):
    """获取工作空间仓库"""
    return request.app.state.workspace_repo_factory()


def get_templates(request: Request):
    """获取模板引擎"""
    return request.app.state.templates


def get_logs_dir(request: Request) -> Path:
    """获取日志目录"""
    return request.app.state.logs_dir


# ============== 数据模型 ==============

class TaskSummary(BaseModel):
    """任务摘要"""
    id: str
    issue_number: int
    title: str
    state: str
    task_type: str
    branch_name: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    retry_count: int = 0
    created_at: str
    updated_at: str
    started_at: str | None = None


class TaskDetail(TaskSummary):
    """任务详情"""
    description: str
    workspace_path: str | None = None
    comments_count: int = 0
    submission_count: int = 0


# ============== API 路由 ==============

@router.get("/api/tasks", response_model=list[TaskSummary])
async def list_tasks(request: Request):
    """获取所有任务列表"""
    task_repo = get_task_repo(request)
    tasks = task_repo.list_all()
    
    result = []
    for task in tasks:
        result.append(TaskSummary(
            id=str(task.id),
            issue_number=task.issue_number,
            title=task.title,
            state=task.state,
            task_type=task.task_type.value,
            branch_name=task.branch_name,
            pr_number=task.pr.number if task.pr else None,
            pr_url=task.pr.html_url if task.pr else None,
            retry_count=task.retry_count,
            created_at=task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=task.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            started_at=task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task.started_at else None,
        ))
    
    # 按更新时间倒序
    result.sort(key=lambda x: x.updated_at, reverse=True)
    return result


@router.get("/api/tasks/{issue_number}", response_model=TaskDetail)
async def get_task(request: Request, issue_number: int):
    """获取任务详情"""
    task_repo = get_task_repo(request)
    workspace_repo = get_workspace_repo(request)
    
    task = task_repo.get_by_issue(issue_number)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Task not found")
    
    workspace = workspace_repo.get(issue_number)
    
    return TaskDetail(
        id=str(task.id),
        issue_number=task.issue_number,
        title=task.title,
        description=task.description,
        state=task.state,
        task_type=task.task_type.value,
        branch_name=task.branch_name,
        pr_number=task.pr.number if task.pr else None,
        pr_url=task.pr.html_url if task.pr else None,
        retry_count=task.retry_count,
        created_at=task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        updated_at=task.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        started_at=task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task.started_at else None,
        workspace_path=str(workspace.path) if workspace else None,
        comments_count=len(task.comments),
        submission_count=task.submission_count,
    )


@router.get("/api/tasks/{issue_number}/output")
async def get_task_output(request: Request, issue_number: int):
    """获取任务实时输出 (SSE 流)"""
    logs_dir = get_logs_dir(request)
    log_file = logs_dir / f"issue_{issue_number}.log"
    
    async def event_generator():
        """SSE 事件生成器"""
        # 先发送历史内容
        if log_file.exists():
            try:
                async with asyncio.timeout(2):
                    async for line in _read_log_file(log_file):
                        yield f"data: {line}\n\n"
            except asyncio.TimeoutError:
                pass
        
        # 持续监听新内容
        last_size = log_file.stat().st_size if log_file.exists() else 0
        last_activity = datetime.now()
        
        while True:
            try:
                # 检查任务是否还在执行
                task_repo = get_task_repo(request)
                task = task_repo.get_by_issue(issue_number)
                
                if task and task.state not in (TaskState.IN_PROGRESS.value, TaskState.PENDING.value):
                    # 任务已完成，发送结束标记后退出
                    yield f"data: [任务已结束: {task.state}]\n\n"
                    break
                
                # 检查文件更新
                if log_file.exists():
                    current_size = log_file.stat().st_size
                    if current_size > last_size:
                        # 读取新增内容
                        async for line in _read_log_file(log_file, skip=last_size):
                            yield f"data: {line}\n\n"
                        last_size = current_size
                        last_activity = datetime.now()
                
                # 超时检查（5分钟无活动则关闭连接）
                if (datetime.now() - last_activity).seconds > 300:
                    yield "data: [连接超时]\n\n"
                    break
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                yield f"data: [错误: {str(e)}]\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


async def _read_log_file(log_file: Path, skip: int = 0) -> Any:
    """异步读取日志文件"""
    import aiofiles
    
    async with aiofiles.open(log_file, "r") as f:
        if skip > 0:
            await f.seek(skip)
        
        async for line in f:
            # 移除 ANSI 颜色代码
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line.rstrip())
            if clean_line:
                yield clean_line


# ============== 页面路由 ==============

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页 - 任务列表"""
    templates = get_templates(request)
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@router.get("/tasks/{issue_number}", response_class=HTMLResponse)
async def task_detail_page(request: Request, issue_number: int):
    """任务详情页"""
    templates = get_templates(request)
    return templates.TemplateResponse(
        "task_detail.html",
        {"request": request, "issue_number": issue_number}
    )
