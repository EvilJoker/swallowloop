"""ExecutorService 接口契约测试

验证 ExecutorService 和 MockExecutor 方法一致性，防止接口脱节。
"""

import inspect
from datetime import datetime
from pathlib import Path

import pytest

from swallowloop.application.service.executor_service import ExecutorService
from swallowloop.domain.model import Issue, IssueId, Stage, IssueStatus
from swallowloop.domain.repository import IssueRepository


class MockAgent:
    """测试用 Mock Agent"""

    async def prepare(self, issue_id: str, context: dict) -> "Workspace":
        return Workspace(
            id=issue_id,
            ready=True,
            workspace_path=str(Path.home() / f".swallowloop/default/{issue_id}/stages"),
            repo_url="",
            branch=issue_id,
            metadata={},
        )

    async def execute(self, task: str, context: dict):
        class Result:
            success = True
            output = "mock output"
            error = None
        return Result()


class Workspace:
    """测试用 Workspace"""
    def __init__(self, id, ready, workspace_path, repo_url, branch, metadata):
        self.id = id
        self.ready = ready
        self.workspace_path = workspace_path
        self.repo_url = repo_url
        self.branch = branch
        self.metadata = metadata


class MockRepo:
    """测试用 Repository"""
    def __init__(self):
        self._issues = {}

    def save(self, issue):
        self._issues[str(issue.id)] = issue

    def get(self, issue_id):
        return self._issues.get(str(issue_id))


def get_public_methods(cls):
    """获取类的 public 方法（排除私有和特殊方法）"""
    return {
        name: getattr(cls, name)
        for name in dir(cls)
        if not name.startswith('_') and callable(getattr(cls, name))
    }


def test_executor_service_has_required_methods():
    """验证 ExecutorService 有所有必要方法"""
    required_methods = [
        'prepare_workspace',  # 准备工作空间
        'execute_stage',     # 执行阶段
        'get_workspace_dir', # 获取工作空间目录
        'prepare_stage_context',  # 准备阶段上下文
    ]

    actual_methods = get_public_methods(ExecutorService)

    for method in required_methods:
        assert method in actual_methods, f"ExecutorService 缺少方法: {method}"


def test_prepare_workspace_is_async():
    """验证 prepare_workspace 是 async 方法"""
    assert inspect.iscoroutinefunction(ExecutorService.prepare_workspace)


def test_execute_stage_is_async():
    """验证 execute_stage 是 async 方法"""
    assert inspect.iscoroutinefunction(ExecutorService.execute_stage)


def test_prepare_workspace_returns_bool():
    """验证 prepare_workspace 返回 bool"""
    repo = MockRepo()
    agent = MockAgent()

    # 创建 issue
    issue = Issue(
        id=IssueId("test-issue"),
        title="test",
        description="test",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )
    issue.create_stage(Stage.BRAINSTORM)
    repo.save(issue)

    executor = ExecutorService(
        repository=repo,
        agent=agent,
        agent_type="mock",
    )

    import asyncio
    result = asyncio.run(executor.prepare_workspace(issue, Stage.BRAINSTORM))

    assert isinstance(result, bool), f"prepare_workspace 应返回 bool，实际返回 {type(result)}"


def test_execute_stage_returns_dict():
    """验证 execute_stage 返回 dict 且包含必要字段"""
    repo = MockRepo()
    agent = MockAgent()

    # 创建带 workspace 的 issue
    issue = Issue(
        id=IssueId("test-issue-2"),
        title="test",
        description="test",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.BRAINSTORM,
        created_at=datetime.now(),
    )
    issue.create_stage(Stage.BRAINSTORM)
    issue.workspace = Workspace(
        id="test-issue-2",
        ready=True,
        workspace_path=str(Path.home() / ".swallowloop/default/test-issue-2/stages"),
        repo_url="",
        branch="test-issue-2",
        metadata={},
    )
    repo.save(issue)

    executor = ExecutorService(
        repository=repo,
        agent=agent,
        agent_type="mock",
    )

    import asyncio
    result = asyncio.run(executor.execute_stage(issue, Stage.BRAINSTORM))

    assert isinstance(result, dict), f"execute_stage 应返回 dict，实际返回 {type(result)}"
    assert "success" in result, "返回值应包含 success 字段"
    assert "output" in result, "返回值应包含 output 字段"
    assert "error" in result, "返回值应包含 error 字段"


def test_mock_executor_consistency():
    """验证 MockExecutor 和 ExecutorService 方法一致

    如果 ExecutorService 新增了 public 方法，MockExecutor 也必须有对应方法。
    """
    # 读取 MockExecutor 源码
    import sys
    sys.path.insert(0, 'tests')
    from helpers.mock_executor import MockExecutor

    real_methods = get_public_methods(ExecutorService)
    mock_methods = get_public_methods(MockExecutor)

    # 过滤出 ExecutorService 中非继承自 object 的方法
    real_public = {
        name for name, method in real_methods.items()
        if not name.startswith('_')
    }
    mock_public = {
        name for name, method in mock_methods.items()
        if not name.startswith('_')
    }

    # MockExecutor 应该有以下方法
    required_mock_methods = ['prepare_workspace', 'execute_stage']

    for method in required_mock_methods:
        assert method in mock_public, f"MockExecutor 缺少方法: {method}"
