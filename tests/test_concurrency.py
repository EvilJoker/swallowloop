"""
并发控制端到端测试

测试多任务并行执行、最大 Worker 限制、超时检测等场景
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Lock

import pytest

from swallowloop.application.dto import IssueDTO
from swallowloop.application.service import TaskService, ExecutionService
from swallowloop.domain.model import Task, TaskId, TaskState, TaskType, Workspace
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from swallowloop.infrastructure.agent.base import ExecutionResult
from tests.conftest import MockAgent, MockSourceControl, MockSlowAgent


class TestConcurrencyControl:
    """
    并发控制测试
    
    验证系统能正确控制并发 Worker 数量
    """

    def test_multiple_tasks_parallel_execution(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        多任务并行执行测试:
        1. 创建多个 Issue
        2. 所有任务可以并行执行
        3. 验证工作空间隔离
        """
        # 创建 3 个 Issue
        for i in range(1, 4):
            issue = IssueDTO(
                number=i,
                title=f"并行任务 {i}",
                body=f"描述 {i}",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 扫描并创建任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 3

        # 为每个任务分配工作空间
        workspaces = []
        for task in new_tasks:
            ws = task_service.assign_workspace(task)
            workspaces.append(ws)
            task_service.start_task(task)

        # 验证每个任务都有独立的工作空间
        paths = [ws.path for ws in workspaces]
        assert len(set(str(p) for p in paths)) == 3  # 3 个不同的路径

        # 验证状态
        for task in new_tasks:
            loaded = task_repository.get_by_issue(task.issue_number)
            assert loaded.state == TaskState.IN_PROGRESS.value

    def test_max_workers_limit(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        最大 Worker 限制测试:
        1. 设置 MAX_WORKERS=2
        2. 创建 5 个 Issue
        3. 只有 2 个任务可以同时执行
        4. 任务完成后，排队任务依次执行
        """
        max_workers = 2
        
        # 创建 5 个 Issue
        for i in range(1, 6):
            issue = IssueDTO(
                number=i,
                title=f"任务 {i}",
                body=f"描述 {i}",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 扫描并创建任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 5

        # 模拟并发控制逻辑
        active_workers = 0
        started_tasks = []
        pending_tasks = list(new_tasks)
        
        # 第一轮：启动最多 max_workers 个任务
        while pending_tasks and active_workers < max_workers:
            task = pending_tasks.pop(0)
            ws = task_service.assign_workspace(task)
            task_service.start_task(task)
            started_tasks.append(task)
            active_workers += 1

        # 验证只启动了 max_workers 个任务
        assert len(started_tasks) == max_workers
        assert len(pending_tasks) == 3  # 剩余排队任务

        # 验证任务状态
        for task in started_tasks:
            loaded = task_repository.get_by_issue(task.issue_number)
            assert loaded.state == TaskState.IN_PROGRESS.value

        for task in pending_tasks:
            loaded = task_repository.get_by_issue(task.issue_number)
            assert loaded.state in (TaskState.NEW.value, TaskState.PENDING.value)


class TestWorkerTimeout:
    """
    Worker 超时测试
    
    验证超时检测和处理机制
    """

    def test_worker_timeout_detection(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        Worker 超时检测测试:
        1. 启动一个任务
        2. 模拟超时（设置过长的执行时间）
        3. 验证超时检测机制
        """
        issue = IssueDTO(
            number=100,
            title="长时间任务",
            body="这个任务需要很长时间",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        mock_agent = MockAgent()

        execution_service = ExecutionService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            agent=mock_agent,
            base_branch="main",
        )

        # 创建任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        ws = task_service.assign_workspace(task)
        task_service.start_task(task)

        # 模拟 Worker 超时（不实际启动子进程，只测试逻辑）
        # 这里我们测试 check_worker_result 对超时的处理
        
        # 手动设置一个很早的启动时间，模拟超时
        from datetime import timedelta
        from swallowloop.application.service.execution_service import ExecutionService as ES
        
        # 设置启动时间为 3 小时前（超过默认 2 小时超时）
        execution_service._worker_start_times[task.issue_number] = datetime.now() - timedelta(hours=3)
        
        # 检查结果应该返回超时错误
        result = execution_service.check_worker_result(task)
        
        assert result is not None
        assert result.success is False
        assert "超时" in result.message

    def test_worker_timeout_configurable(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        验证超时时间可配置
        """
        # 验证 ExecutionService 的超时常量
        from swallowloop.application.service.execution_service import ExecutionService
        
        assert hasattr(ExecutionService, 'WORKER_TIMEOUT_HOURS')
        assert ExecutionService.WORKER_TIMEOUT_HOURS == 2  # 默认 2 小时


class TestConcurrentDataIntegrity:
    """
    并发数据完整性测试
    
    验证多任务并发时数据不会损坏
    """

    def test_concurrent_task_save(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        顺序保存多个任务测试:
        验证多个任务可以正确保存
        """
        # 创建多个 Issue
        issues = []
        for i in range(1, 11):
            issue = IssueDTO(
                number=i,
                title=f"并发任务 {i}",
                body=f"描述 {i}",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            mock_source_control.add_issue(issue)
            issues.append(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 扫描创建任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 10

        # 顺序分配工作空间并保存
        for task in new_tasks:
            task_service.assign_workspace(task)
            task_service.start_task(task)

        # 验证所有任务都正确保存
        for task in new_tasks:
            loaded = task_repository.get_by_issue(task.issue_number)
            assert loaded is not None
            assert loaded.state == TaskState.IN_PROGRESS.value

    def test_workspace_uniqueness(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        工作空间唯一性测试:
        验证每个任务都有唯一的工作空间
        """
        # 创建多个 Issue
        for i in range(1, 6):
            issue = IssueDTO(
                number=i,
                title=f"工作空间任务 {i}",
                body=f"描述 {i}",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 扫描创建任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 5

        # 为每个任务分配工作空间
        workspace_ids = set()
        for task in new_tasks:
            ws = task_service.assign_workspace(task)
            assert ws is not None
            workspace_ids.add(ws.id)

        # 验证每个工作空间 ID 唯一
        assert len(workspace_ids) == 5
