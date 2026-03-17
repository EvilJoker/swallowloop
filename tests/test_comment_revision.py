"""
评论触发修改端到端测试

测试用户评论触发任务修订的流程
"""

from datetime import datetime

import pytest

from swallowloop.application.dto import IssueDTO
from swallowloop.application.service import TaskService
from swallowloop.domain.model import (
    Comment,
    PullRequest,
    Task,
    TaskId,
    TaskState,
    TaskType,
    Workspace,
)
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from tests.conftest import MockSourceControl


class TestCommentDetection:
    """
    评论检测端到端测试

    验证系统检测用户评论的能力
    """

    def test_detect_new_comment(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """应检测到新评论"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "https://github.com/test/repo/pull/101")

        # 添加用户评论（使用字符串形式）
        mock_source_control.add_comment(sample_issue.number, "Please add more tests", "reviewer")

        # 扫描应检测到评论
        task_service.scan_issues()

        # 重新加载任务
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded is not None
        assert loaded.state == TaskState.PENDING.value

    def test_ignore_bot_comments(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """应忽略机器人评论"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "https://github.com/test/repo/pull/101")

        # 添加机器人评论（Bot 评论以 swallowloop 开头）
        mock_source_control.add_comment(sample_issue.number, "[SwallowLoop Bot] PR created", "swallowloop-bot")

        # 扫描
        task_service.scan_issues()

        # 任务状态应保持 submitted
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded is not None
        assert loaded.state == TaskState.SUBMITTED.value

    def test_skip_already_processed_comments(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """应跳过已处理的评论"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "https://github.com/test/repo/pull/101")

        # 添加评论
        mock_source_control.add_comment(sample_issue.number, "Fix this", "reviewer")

        # 第一次扫描触发修订
        task_service.scan_issues()

        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.state == TaskState.PENDING.value

        # 完成修订并重新提交
        loaded.begin_execution()
        loaded.submit_pr(PullRequest(
            number=102,
            html_url="url2",
            branch_name="branch",
            title="title",
        ))
        task_repository.save(loaded)

        # 再次扫描（评论已处理）
        task_service.scan_issues()

        # 状态应保持 submitted
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.state == TaskState.SUBMITTED.value


class TestRevisionFlow:
    """
    修订流程端到端测试

    验证完整的修订流程
    """

    def test_revision_changes_task_type(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """修订应改变任务类型"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "url")

        assert task.task_type == TaskType.NEW_TASK

        # 添加评论触发修订
        mock_source_control.add_comment(sample_issue.number, "Fix it", "reviewer")
        task_service.scan_issues()

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.task_type == TaskType.REVISION

    def test_revision_resets_retry_count(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """修订应重置重试计数"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建任务并模拟重试
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 模拟重试
        task.increment_retry()
        task.increment_retry()
        task_repository.save(task)

        # 提交
        task_service.submit_task(task, 101, "url")

        # 触发修订
        mock_source_control.add_comment(sample_issue.number, "Fix", "reviewer")
        task_service.scan_issues()

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.retry_count == 0

    def test_revision_preserves_workspace(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """修订应保留工作空间"""
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
        original_workspace = task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "url")

        # 触发修订
        mock_source_control.add_comment(sample_issue.number, "Fix", "reviewer")
        task_service.scan_issues()

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.workspace is not None
        assert loaded.workspace.id == original_workspace.id

    def test_revision_preserves_pr(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """修订应保留 PR"""
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

        # 触发修订
        mock_source_control.add_comment(sample_issue.number, "Fix", "reviewer")
        task_service.scan_issues()

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.pr is not None
        assert loaded.pr.number == 101


class TestMultipleRevisions:
    """
    多次修订端到端测试

    验证多次修订的场景
    """

    def test_multiple_user_comments(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """多个用户评论应累积"""
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
        task_service.submit_task(task, 101, "url")

        # 第一次评论触发修订
        mock_source_control.add_comment(sample_issue.number, "Fix A", "reviewer1")
        task_service.scan_issues()

        # 完成第一次修订
        loaded = task_repository.get_by_issue(sample_issue.number)
        loaded.begin_execution()
        loaded.submit_pr(PullRequest(
            number=102,
            html_url="url2",
            branch_name="branch",
            title="title",
        ))
        task_repository.save(loaded)

        # 第二次评论
        mock_source_control.add_comment(sample_issue.number, "Fix B", "reviewer2")
        task_service.scan_issues()

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert len(loaded.comments) == 2

    def test_revision_count_increases(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """多次修订应增加提交计数"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 第一次提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 101, "url")

        assert task.submission_count == 1

        # 第一次修订
        mock_source_control.add_comment(sample_issue.number, "Fix", "reviewer")
        task_service.scan_issues()

        loaded = task_repository.get_by_issue(sample_issue.number)
        loaded.begin_execution()
        loaded.submit_pr(PullRequest(number=102, html_url="url2", branch_name="b", title="t"))
        task_repository.save(loaded)

        assert loaded.submission_count == 2