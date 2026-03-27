"""ExecutorWorkerPool 模块测试"""

import pytest
import time
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.application.service.worker_pool import ExecutorWorkerPool
from tests.helpers import MockRepository, MockExecutor


@pytest.fixture
def repo():
    return MockRepository()


@pytest.fixture
def executor(repo):
    return MockExecutor(repository=repo)


@pytest.fixture
def worker_pool(executor):
    return ExecutorWorkerPool(executor=executor, max_workers=2)


@pytest.fixture
def issue(repo):
    issue = Issue(
        id=IssueId("test-issue"),
        title="测试",
        description="测试描述",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )
    issue.create_stage(Stage.BRAINSTORM)
    repo.save(issue)
    return issue


class TestExecutorWorkerPool:
    """ExecutorWorkerPool 功能测试"""

    def test_submit_success(self, worker_pool, repo, issue):
        """成功提交任务"""
        result = worker_pool.submit(str(issue.id), Stage.BRAINSTORM)
        assert result is True

    def test_submit_duplicate_returns_false(self, worker_pool, repo, issue):
        """重复提交返回 False"""
        # 第一次提交
        result1 = worker_pool.submit(str(issue.id), Stage.BRAINSTORM)
        assert result1 is True

        # 第二次提交同一个任务
        result2 = worker_pool.submit(str(issue.id), Stage.BRAINSTORM)
        assert result2 is False

    def test_is_running(self, worker_pool, repo, issue):
        """检查任务是否运行中"""
        # 初始不是运行中
        assert worker_pool.is_running(str(issue.id), Stage.BRAINSTORM) is False

        # 提交后是运行中
        worker_pool.submit(str(issue.id), Stage.BRAINSTORM)
        assert worker_pool.is_running(str(issue.id), Stage.BRAINSTORM) is True

    def test_is_running_different_stages(self, worker_pool, repo, issue):
        """不同阶段任务互不影响"""
        # 提交 BRAINSTORM
        worker_pool.submit(str(issue.id), Stage.BRAINSTORM)
        assert worker_pool.is_running(str(issue.id), Stage.BRAINSTORM) is True
        assert worker_pool.is_running(str(issue.id), Stage.PLAN_FORMED) is False

    def test_shutdown(self, worker_pool):
        """关闭线程池"""
        worker_pool.shutdown()
        # shutdown 后线程池不再接受新任务，不报错即可

    def test_submit_different_issues(self, worker_pool, repo):
        """不同 Issue 可以同时提交"""
        issue1 = Issue(
            id=IssueId("issue-1"),
            title="测试1",
            description="描述1",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue1.create_stage(Stage.BRAINSTORM)
        repo.save(issue1)

        issue2 = Issue(
            id=IssueId("issue-2"),
            title="测试2",
            description="描述2",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue2.create_stage(Stage.BRAINSTORM)
        repo.save(issue2)

        result1 = worker_pool.submit("issue-1", Stage.BRAINSTORM)
        result2 = worker_pool.submit("issue-2", Stage.BRAINSTORM)

        assert result1 is True
        assert result2 is True
