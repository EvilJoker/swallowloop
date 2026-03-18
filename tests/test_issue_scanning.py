"""
Issue 扫描与任务创建端到端测试

测试从 GitHub Issue 扫描到任务创建的完整流程
"""

from datetime import datetime

import pytest

from swallowloop.application.dto import IssueDTO
from swallowloop.application.service import TaskService
from swallowloop.domain.model import TaskState
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from tests.conftest import MockSourceControl


class TestIssueScanning:
    """
    Issue 扫描端到端测试

    验证从 Issue 创建任务的完整流程
    """

    def test_scan_creates_new_task(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """扫描 Issue 应创建新任务"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()

        assert len(new_tasks) == 1
        assert new_tasks[0].issue_number == sample_issue.number
        assert new_tasks[0].title == sample_issue.title
        assert new_tasks[0].state == TaskState.NEW.value

    def test_scan_ignores_closed_issues(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """扫描应忽略已关闭的 Issue"""
        mock_source_control.add_issue(sample_issue)
        mock_source_control.remove_issue(sample_issue.number)  # 关闭 Issue

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()

        assert len(new_tasks) == 0

    def test_scan_with_multiple_issues(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """扫描多个 Issue"""
        issues = [
            IssueDTO(
                number=i,
                title=f"Issue {i}",
                body=f"Body {i}",
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

        assert len(new_tasks) == 3

    def test_scan_skips_existing_tasks(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """扫描应跳过已存在的任务"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 第一次扫描创建任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 1

        # 第二次扫描不应创建新任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 0

    def test_scan_detects_closed_issues_for_abort(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """扫描应检测已关闭的 Issue 并返回需要中止的任务"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]

        # 分配工作空间并开始执行
        workspace = task_service.assign_workspace(task)
        task_service.start_task(task)

        # 关闭 Issue
        mock_source_control.remove_issue(sample_issue.number)

        # 扫描应返回需要中止的任务
        _, tasks_to_abort = task_service.scan_issues()
        assert len(tasks_to_abort) == 1
        assert tasks_to_abort[0].issue_number == sample_issue.number


class TestTaskCreation:
    """
    任务创建端到端测试

    验证从 Issue 创建任务的正确性
    """

    def test_create_task_from_issue(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """从 Issue 创建任务"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]

        assert task.issue_number == sample_issue.number
        assert task.title == sample_issue.title
        assert task.description == sample_issue.body
        assert task.state == TaskState.NEW.value
        assert task.branch_name.startswith("feature_1")

    def test_create_task_generates_correct_branch_name(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """任务应生成正确的分支名"""
        issue = IssueDTO(
            number=42,
            title="Fix the critical bug in authentication module!!!",
            body="Description",
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

        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]

        # 验证分支名格式: {type}_{issue_number}_{date}-{slug}
        assert "feature_42" in task.branch_name
        # 特殊字符应被移除
        assert "!" not in task.branch_name
        assert "   " not in task.branch_name

    def test_task_persisted_after_creation(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """任务创建后应持久化"""
        mock_source_control.add_issue(sample_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        task_service.scan_issues()

        # 从仓库重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded is not None
        assert loaded.issue_number == sample_issue.number


class TestLabelFiltering:
    """
    标签过滤端到端测试

    验证只处理带有正确标签的 Issue
    """

    def test_only_processes_labeled_issues(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """只处理带有指定标签的 Issue"""
        # 正确标签的 Issue
        labeled_issue = IssueDTO(
            number=1,
            title="Labeled Issue",
            body="Body",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # 无标签的 Issue
        unlabeled_issue = IssueDTO(
            number=2,
            title="Unlabeled Issue",
            body="Body",
            state="open",
            labels=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_source_control.add_issue(labeled_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        new_tasks, _ = task_service.scan_issues()

        assert len(new_tasks) == 1
        assert new_tasks[0].issue_number == 1

    def test_custom_label(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """使用自定义标签"""
        custom_issue = IssueDTO(
            number=1,
            title="Custom Label Issue",
            body="Body",
            state="open",
            labels=["custom-label"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_source_control.add_issue(custom_issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="custom-label",
        )

        new_tasks, _ = task_service.scan_issues()

        assert len(new_tasks) == 1
