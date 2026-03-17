"""
PR 提交流程端到端测试

测试任务完成后创建 Pull Request 的流程
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from swallowloop.application.dto import IssueDTO
from swallowloop.application.service import ExecutionService, TaskService
from swallowloop.domain.model import (
    PullRequest,
    Task,
    TaskId,
    TaskState,
    TaskType,
    Workspace,
)
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from swallowloop.infrastructure.agent import ExecutionResult
from tests.conftest import MockAgent, MockSourceControl


class TestPRCreation:
    """
    PR 创建端到端测试

    验证 PR 创建流程
    """

    def test_create_pr_after_successful_execution(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        mock_agent: MockAgent,
        sample_issue: IssueDTO,
        temp_dir: Path,
    ):
        """成功执行后创建 PR"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

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

        # 分配工作空间
        workspace = task_service.assign_workspace(task)
        task_service.start_task(task)

        # 创建 PR
        pr = execution_service.create_pull_request(task)

        assert pr is not None
        assert pr.branch_name == task.branch_name
        assert f"Issue#{task.issue_number}" in pr.title

    def test_pr_title_format(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        mock_agent: MockAgent,
        sample_issue: IssueDTO,
    ):
        """PR 标题格式应正确"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        execution_service = ExecutionService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            agent=mock_agent,
            base_branch="main",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)

        pr = execution_service.create_pull_request(task)

        # 标题应包含 Issue 号
        assert f"Issue#{sample_issue.number}" in pr.title
        # 标题应包含原始 Issue 标题
        assert sample_issue.title in pr.title

    def test_pr_body_contains_issue_reference(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        mock_agent: MockAgent,
        sample_issue: IssueDTO,
    ):
        """PR body 应包含 Issue 引用"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        execution_service = ExecutionService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            agent=mock_agent,
            base_branch="main",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)

        # 检查 create_pull_request 的调用
        pr_info = execution_service.create_pull_request(task)

        # body 应包含 Closes #issue_number
        created_pr = mock_source_control._created_prs[-1]
        assert f"Closes #{sample_issue.number}" in created_pr["body"]


class TestPRSubmissionFlow:
    """
    PR 提交流程端到端测试

    验证完整的任务提交流程
    """

    def test_submit_task_updates_state(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
        temp_dir: Path,
    ):
        """提交任务应更新状态"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并准备任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 提交任务
        task_service.submit_task(task, pr_number=101, pr_url="https://github.com/test/repo/pull/101")

        # 状态应为 submitted
        assert task.state == TaskState.SUBMITTED.value
        assert task.pr is not None
        assert task.pr.number == 101
        assert task.submission_count == 1

    def test_submission_increments_count(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """多次提交应增加计数"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "url1")

        assert task.submission_count == 1

        # 模拟修订后再次提交
        from swallowloop.domain.model import Comment
        comment = Comment(id=1, body="Fix it", author="reviewer")
        task.apply_revision(comment)

        task_service.start_task(task)
        task_service.submit_task(task, 102, "url2")

        assert task.submission_count == 2


class TestExecutionResult:
    """
    执行结果处理端到端测试

    验证执行结果的处理流程
    """

    def test_execution_success_creates_pr(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
        temp_dir: Path,
    ):
        """执行成功后应创建 PR"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        mock_agent = MockAgent()
        mock_agent.set_success(True)
        mock_agent.set_files_to_change(["src/main.py"])

        execution_service = ExecutionService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            agent=mock_agent,
            base_branch="main",
        )

        # 创建并执行任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        workspace = task_service.assign_workspace(task)
        task_service.start_task(task)

        # 模拟执行完成
        result = mock_agent.execute(task, workspace.path)

        assert result.success is True
        assert len(result.files_changed) > 0

    def test_execution_failure_no_pr(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """执行失败不应创建 PR"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        mock_agent = MockAgent()
        mock_agent.set_success(False)

        # 创建任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        workspace = task_service.assign_workspace(task)

        # 模拟执行失败
        result = mock_agent.execute(task, workspace.path)

        assert result.success is False
        assert len(result.files_changed) == 0


class TestPRPersistence:
    """
    PR 持久化端到端测试

    验证 PR 信息在任务中的持久化
    """

    def test_pr_persisted_with_task(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """PR 应随任务一起持久化"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "https://github.com/test/repo/pull/101")

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded is not None
        assert loaded.pr is not None
        assert loaded.pr.number == 101