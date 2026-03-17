"""
任务生命周期端到端测试

测试任务从创建到完成的完整状态流转
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


class TestTaskStateLifecycle:
    """
    任务状态机端到端测试

    验证任务状态流转的完整生命周期：
    new → assigned → pending → in_progress → submitted → completed
    """

    def test_new_task_initial_state(self, sample_task: Task):
        """新任务初始状态应为 new"""
        assert sample_task.state == TaskState.NEW.value
        assert sample_task.is_active is True
        assert sample_task.retry_count == 0
        assert sample_task.submission_count == 0

    def test_assign_workspace_transitions_to_assigned(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
    ):
        """分配工作空间后状态变为 assigned"""
        sample_task.assign_workspace(sample_workspace)

        assert sample_task.state == TaskState.ASSIGNED.value
        assert sample_task.workspace == sample_workspace
        assert len(sample_task.events) == 1
        assert sample_task.events[0].__class__.__name__ == "TaskAssigned"

    def test_mark_ready_transitions_to_pending(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
    ):
        """标记就绪后状态变为 pending"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()

        assert sample_task.state == TaskState.PENDING.value

    def test_begin_execution_transitions_to_in_progress(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
    ):
        """开始执行后状态变为 in_progress"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()

        assert sample_task.state == TaskState.IN_PROGRESS.value
        assert sample_task.started_at is not None
        assert len(sample_task.events) == 2

    def test_submit_pr_transitions_to_submitted(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
    ):
        """提交 PR 后状态变为 submitted"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)

        assert sample_task.state == TaskState.SUBMITTED.value
        assert sample_task.pr == sample_pr
        assert sample_task.submission_count == 1

    def test_complete_transitions_to_completed(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
    ):
        """完成后状态变为 completed"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)
        sample_task.mark_completed()

        assert sample_task.state == TaskState.COMPLETED.value
        assert sample_task.is_active is False


class TestTaskRetryMechanism:
    """
    任务重试机制端到端测试

    验证执行失败后的重试逻辑
    """

    def test_can_retry_within_limit(self, sample_task: Task):
        """在重试限制内可以重试"""
        assert sample_task.can_retry() is True
        assert sample_task.retry_count == 0

    def test_cannot_retry_after_max_retries(self, sample_task: Task):
        """达到最大重试次数后不能重试"""
        # 达到最大重试次数
        for _ in range(sample_task._max_retries):
            sample_task.increment_retry()

        assert sample_task.can_retry() is False

    def test_do_retry_transitions_to_pending(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
    ):
        """重试后状态变为 pending"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()

        # 模拟失败重试
        sample_task.increment_retry()
        sample_task.do_retry()

        assert sample_task.state == TaskState.PENDING.value
        assert sample_task.retry_count == 1

    def test_retry_preserves_workspace(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
    ):
        """重试后工作空间应保留"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.increment_retry()
        sample_task.do_retry()

        assert sample_task.workspace == sample_workspace


class TestTaskAbortMechanism:
    """
    任务终止机制端到端测试

    验证任务中止的各种情况
    """

    def test_abort_from_in_progress(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
    ):
        """从 in_progress 状态终止"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.do_abort()

        assert sample_task.state == TaskState.ABORTED.value
        assert sample_task.is_active is False

    def test_abort_from_submitted(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
    ):
        """从 submitted 状态终止"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)
        sample_task.do_abort()

        assert sample_task.state == TaskState.ABORTED.value


class TestTaskRevisionFlow:
    """
    任务修订流程端到端测试

    验证用户评论触发任务修订的流程
    """

    def test_apply_revision_transitions_to_pending(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
        sample_comment: Comment,
    ):
        """应用修订后状态变为 pending"""
        # 完成正常流程
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)

        # 用户评论触发修订
        sample_task.apply_revision(sample_comment)

        assert sample_task.state == TaskState.PENDING.value
        assert sample_task.task_type == TaskType.REVISION
        assert sample_task.latest_comment == sample_comment
        assert sample_task.retry_count == 0  # 重置重试计数

    def test_revision_preserves_pr(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
        sample_comment: Comment,
    ):
        """修订后 PR 应保留"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)
        sample_task.apply_revision(sample_comment)

        assert sample_task.pr == sample_pr

    def test_multiple_revisions(
        self,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
    ):
        """多次修订流程"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)

        # 第一次修订
        comment1 = Comment(id=1, body="Fix the typo", author="reviewer")
        sample_task.apply_revision(comment1)
        assert sample_task.state == TaskState.PENDING.value

        # 完成修订
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)

        # 第二次修订
        comment2 = Comment(id=2, body="Add tests", author="reviewer")
        sample_task.apply_revision(comment2)
        assert sample_task.state == TaskState.PENDING.value
        assert len(sample_task.comments) == 2


class TestTaskPersistence:
    """
    任务持久化端到端测试

    验证任务保存和恢复的正确性
    """

    def test_save_and_load_task(
        self,
        task_repository: TaskRepository,
        sample_task: Task,
    ):
        """保存和加载任务"""
        task_repository.save(sample_task)

        loaded = task_repository.get_by_issue(sample_task.issue_number)
        assert loaded is not None
        assert str(loaded.id) == str(sample_task.id)
        assert loaded.title == sample_task.title
        assert loaded.state == sample_task.state

    def test_save_task_with_workspace_and_pr(
        self,
        task_repository: TaskRepository,
        sample_task: Task,
        sample_workspace: Workspace,
        sample_pr: PullRequest,
    ):
        """保存带有工作空间和 PR 的任务"""
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)

        task_repository.save(sample_task)

        loaded = task_repository.get_by_issue(sample_task.issue_number)
        assert loaded is not None
        assert loaded.workspace is not None
        assert loaded.pr is not None
        assert loaded.state == TaskState.SUBMITTED.value

    def test_list_active_tasks(
        self,
        task_repository: TaskRepository,
        sample_task: Task,
    ):
        """列出活跃任务"""
        task_repository.save(sample_task)

        active = task_repository.list_active()
        assert len(active) == 1

        # 完成任务后不应出现在活跃列表
        sample_workspace = Workspace(
            id="ws1",
            issue_number=1,
            branch_name="test",
            path="/tmp/test",
        )
        sample_pr = PullRequest(
            number=1,
            html_url="https://github.com/test/repo/pull/1",
            branch_name="test",
            title="Test PR",
        )
        sample_task.assign_workspace(sample_workspace)
        sample_task.mark_ready()
        sample_task.begin_execution()
        sample_task.submit_pr(sample_pr)
        sample_task.mark_completed()

        task_repository.save(sample_task)

        active = task_repository.list_active()
        assert len(active) == 0
