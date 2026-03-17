"""
工作空间分配端到端测试

测试工作空间的创建、分配和管理
"""

from datetime import datetime
from pathlib import Path

import pytest

from swallowloop.application.dto import IssueDTO
from swallowloop.application.service import TaskService
from swallowloop.domain.model import (
    PullRequest,
    Task,
    TaskId,
    TaskState,
    Workspace,
)
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from tests.conftest import MockSourceControl


class TestWorkspaceAssignment:
    """
    工作空间分配端到端测试

    验证工作空间分配流程
    """

    def test_assign_workspace_creates_workspace(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """分配工作空间应创建工作空间"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]

        workspace = task_service.assign_workspace(task)

        assert workspace is not None
        assert workspace.issue_number == sample_issue.number
        assert workspace.branch_name == task.branch_name

    def test_assign_workspace_updates_task_state(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """分配工作空间后任务状态应更新"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]

        task_service.assign_workspace(task)

        # 状态应变为 pending（assign + mark_ready）
        assert task.state == TaskState.PENDING.value

    def test_assign_workspace_sets_repo_url(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """分配工作空间应设置仓库 URL"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]

        task_service.assign_workspace(task)

        assert task.repo_url is not None
        assert "github.com" in task.repo_url

    def test_workspace_persisted_after_assignment(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """工作空间分配后应持久化"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        workspace = task_service.assign_workspace(task)

        # 从仓库重新加载
        loaded = workspace_repository.get(sample_issue.number)
        assert loaded is not None
        assert loaded.id == workspace.id


class TestWorkspaceManagement:
    """
    工作空间管理端到端测试

    验证工作空间的存储和释放
    """

    def test_workspace_persistence(
        self,
        workspace_repository: WorkspaceRepository,
        temp_dir: Path,
    ):
        """工作空间持久化测试"""
        workspace = Workspace(
            id="issue1_20260317",
            issue_number=1,
            branch_name="Issue1_test",
            path=temp_dir / "issue1_20260317",
        )

        workspace_repository.save(workspace)

        loaded = workspace_repository.get(1)
        assert loaded is not None
        assert loaded.id == workspace.id
        assert loaded.issue_number == workspace.issue_number

    def test_release_workspace(
        self,
        workspace_repository: WorkspaceRepository,
        temp_dir: Path,
    ):
        """释放工作空间测试"""
        workspace = Workspace(
            id="issue1_20260317",
            issue_number=1,
            branch_name="Issue1_test",
            path=temp_dir / "issue1_20260317",
        )

        workspace_repository.save(workspace)

        # 释放
        result = workspace_repository.release(1)
        assert result is True

        # 释放后不应找到
        loaded = workspace_repository.get(1)
        assert loaded is None

    def test_list_active_workspaces(
        self,
        workspace_repository: WorkspaceRepository,
        temp_dir: Path,
    ):
        """列出活跃工作空间测试"""
        for i in range(1, 4):
            workspace = Workspace(
                id=f"issue{i}_20260317",
                issue_number=i,
                branch_name=f"Issue{i}_test",
                path=temp_dir / f"issue{i}_20260317",
            )
            workspace_repository.save(workspace)

        active = workspace_repository.list_active()
        assert len(active) == 3

        # 释放一个
        workspace_repository.release(1)

        active = workspace_repository.list_active()
        assert len(active) == 2


class TestWorkspacePathGeneration:
    """
    工作空间路径生成端到端测试

    验证工作空间路径的正确生成
    """

    def test_workspace_path_format(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """工作空间路径格式应正确"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        workspace = task_service.assign_workspace(task)

        # 路径应包含 issue 号
        assert f"issue{sample_issue.number}" in str(workspace.path)
        # 路径应在 .swallowloop 目录下
        assert ".swallowloop" in str(workspace.path)

    def test_workspace_id_uniqueness(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """每个工作空间应有唯一 ID"""
        issues = [
            IssueDTO(
                number=i,
                title=f"Issue {i}",
                body="Body",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        for issue in issues:
            mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        workspace_ids = set()

        for task in new_tasks:
            workspace = task_service.assign_workspace(task)
            workspace_ids.add(workspace.id)

        # 所有 ID 应唯一
        assert len(workspace_ids) == 3
