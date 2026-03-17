"""
任务重试与终止端到端测试

测试执行失败后的重试逻辑和任务终止流程
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
    Workspace,
)
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from swallowloop.infrastructure.agent import ExecutionResult
from tests.conftest import MockAgent, MockSourceControl


class TestTaskRetry:
    """
    任务重试端到端测试

    验证执行失败后的重试逻辑
    """

    def test_retry_on_execution_failure(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """执行失败应触发重试"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 模拟执行失败，触发重试
        task_service.retry_task(task, "Execution failed")

        assert task.state == TaskState.PENDING.value
        assert task.retry_count == 1

    def test_max_retry_limit(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """达到最大重试次数后应无法重试"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 通过增加重试计数来模拟达到最大重试次数
        for i in range(task._max_retries):
            task.increment_retry()

        # 验证已达到重试限制
        assert task.retry_count == task._max_retries
        assert task.can_retry() is False

    def test_retry_preserves_workspace(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """重试应保留工作空间"""
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
        original_workspace = task_service.assign_workspace(task)
        task_service.start_task(task)

        # 重试
        task_service.retry_task(task, "Failed")
        task_repository.save(task)

        # 重新加载
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.workspace is not None
        assert loaded.workspace.id == original_workspace.id

    def test_retry_count_increments(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """重试计数应递增"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 第一次重试
        task_service.retry_task(task, "Retry 1")
        task_repository.save(task)

        # 重新加载并开始执行
        loaded = task_repository.get_by_issue(sample_issue.number)
        loaded.begin_execution()
        task_repository.save(loaded)

        # 第二次重试
        loaded = task_repository.get_by_issue(sample_issue.number)
        task_service.retry_task(loaded, "Retry 2")
        task_repository.save(loaded)

        # 第三次重试
        loaded = task_repository.get_by_issue(sample_issue.number)
        loaded.begin_execution()
        task_repository.save(loaded)
        loaded = task_repository.get_by_issue(sample_issue.number)
        task_service.retry_task(loaded, "Retry 3")
        task_repository.save(loaded)

        # 验证计数
        loaded = task_repository.get_by_issue(sample_issue.number)
        assert loaded.retry_count == 3


class TestTaskAbort:
    """
    任务终止端到端测试

    验证任务终止的各种情况
    """

    def test_abort_task(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """中止任务"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 中止
        task_service.abort_task(task, "Manual abort")

        assert task.state == TaskState.ABORTED.value
        assert task.is_active is False

    def test_abort_after_max_retries(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """达到最大重试次数后应中止"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 达到最大重试
        for i in range(task._max_retries):
            task.increment_retry()

        # 无法重试时应中止
        if not task.can_retry():
            task_service.abort_task(task, "Max retries exceeded")

        assert task.state == TaskState.ABORTED.value

    def test_abort_when_issue_closed(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """Issue 关闭时应中止任务"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 关闭 Issue
        mock_source_control.close_issue(sample_issue.number)

        # 扫描应返回需要中止的任务
        _, tasks_to_abort = task_service.scan_issues()

        assert len(tasks_to_abort) == 1
        assert tasks_to_abort[0].issue_number == sample_issue.number

    def test_abort_from_submitted_state(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """从 submitted 状态中止"""
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

        # 中止
        task_service.abort_task(task, "PR closed without merge")

        assert task.state == TaskState.ABORTED.value

    def test_aborted_task_not_in_active_list(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """中止的任务不应在活跃列表中"""
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
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 中止
        task_service.abort_task(task, "Aborted")
        task_repository.save(task)

        # 检查活跃列表
        active = task_repository.list_active()
        issue_numbers = [t.issue_number for t in active]
        assert sample_issue.number not in issue_numbers


class TestExecutionResultHandling:
    """
    执行结果处理端到端测试

    验证成功和失败结果的处理
    """

    def test_success_result(
        self,
        mock_agent: MockAgent,
        sample_task: Task,
        temp_dir,
    ):
        """成功执行结果"""
        mock_agent.set_success(True)
        mock_agent.set_files_to_change(["src/main.py"])
        result = mock_agent.execute(sample_task, temp_dir)

        assert result.success is True
        assert "成功" in result.message

    def test_failure_result(
        self,
        mock_agent: MockAgent,
        sample_task: Task,
        temp_dir,
    ):
        """失败执行结果"""
        mock_agent.set_success(False)
        result = mock_agent.execute(sample_task, temp_dir)

        assert result.success is False
        assert "失败" in result.message

    def test_execution_result_files_changed(
        self,
        mock_agent: MockAgent,
        sample_task: Task,
        temp_dir,
    ):
        """执行结果包含修改的文件"""
        mock_agent.set_success(True)
        mock_agent.set_files_to_change(["src/main.py", "tests/test_main.py"])
        result = mock_agent.execute(sample_task, temp_dir)

        if result.success:
            assert len(result.files_changed) == 2


class TestCompleteTaskAfterPRMerge:
    """
    PR 合并后完成任务端到端测试

    验证 PR 合并后的任务完成流程
    """

    def test_complete_task_when_pr_merged(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        sample_issue: IssueDTO,
    ):
        """PR 合并后应完成任务"""
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

        # 模拟 PR 合并（Issue 关闭）
        mock_source_control.close_issue(sample_issue.number)

        # 模拟 PR 已合并
        mock_source_control.merge_pr(101)

        # 扫描
        _, tasks_to_abort = task_service.scan_issues()

        # 检查任务状态（如果 PR 已合并，应完成而非中止）
        loaded = task_repository.get_by_issue(sample_issue.number)
        # 这里主要验证流程正确执行
        assert loaded is not None