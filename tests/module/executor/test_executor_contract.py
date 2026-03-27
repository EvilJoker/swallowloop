"""ExecutorService 接口契约测试

验证 IExecutor 接口实现的一致性。
"""

import inspect
from datetime import datetime
from pathlib import Path

import pytest

from swallowloop.application.service.executor import IExecutor
from swallowloop.application.service.executor_service import ExecutorService
from swallowloop.domain.model import Issue, IssueId, Stage, IssueStatus
from swallowloop.domain.model.workspace import Workspace
from swallowloop.infrastructure.agent.base import BaseAgent, AgentResult
from swallowloop.infrastructure.agent.mock_agent import MockAgent
from swallowloop.infrastructure.agent.deerflow_agent import DeerFlowAgent


class TestIExecutorContract:
    """验证 IExecutor 接口契约"""

    def get_abstract_methods(self, cls):
        """获取类的抽象方法"""
        return {
            name for name in dir(cls)
            if not name.startswith('_') and getattr(cls, name, None) is not None
        }

    def get_public_methods(self, cls):
        """获取类的 public 方法（排除私有和特殊方法）"""
        return {
            name for name in dir(cls)
            if not name.startswith('_') and callable(getattr(cls, name))
        }

    def test_executor_service_implements_iexecutor(self):
        """验证 ExecutorService 实现了 IExecutor 接口"""
        abstract_methods = self.get_abstract_methods(IExecutor)
        executor_methods = self.get_public_methods(ExecutorService)

        # IExecutor 的抽象方法必须在 ExecutorService 中实现
        for method in abstract_methods:
            assert method in executor_methods, f"IExecutor 方法 {method} 未在 ExecutorService 中实现"

    def test_prepare_workspace_is_async(self):
        """验证 prepare_workspace 是 async 方法"""
        assert inspect.iscoroutinefunction(ExecutorService.prepare_workspace)

    def test_execute_stage_is_async(self):
        """验证 execute_stage 是 async 方法"""
        assert inspect.iscoroutinefunction(ExecutorService.execute_stage)

    def test_prepare_workspace_signature(self):
        """验证 prepare_workspace 方法签名"""
        sig = inspect.signature(ExecutorService.prepare_workspace)
        params = list(sig.parameters.keys())
        # self, issue, stage
        assert 'issue' in params
        assert 'stage' in params


class TestAgentInterfaceContract:
    """验证 Agent 接口契约"""

    def get_abstract_methods(self, cls):
        """获取类的抽象方法"""
        methods = set()
        for name in dir(cls):
            if name.startswith('_'):
                continue
            attr = getattr(cls, name, None)
            if attr and hasattr(attr, '__isabstractmethod__') and attr.__isabstractmethod__:
                methods.add(name)
        return methods

    def test_mock_agent_implements_base_agent(self):
        """验证 MockAgent 实现了 BaseAgent 接口"""
        abstract_methods = self.get_abstract_methods(BaseAgent)
        mock_methods = self.get_public_methods(MockAgent)

        for method in abstract_methods:
            assert method in mock_methods, f"MockAgent 未实现 BaseAgent 方法: {method}"

    def test_deerflow_agent_implements_base_agent(self):
        """验证 DeerFlowAgent 实现了 BaseAgent 接口"""
        abstract_methods = self.get_abstract_methods(BaseAgent)
        deerflow_methods = self.get_public_methods(DeerFlowAgent)

        for method in abstract_methods:
            assert method in deerflow_methods, f"DeerFlowAgent 未实现 BaseAgent 方法: {method}"

    def get_public_methods(self, cls):
        """获取类的 public 方法"""
        return {
            name for name in dir(cls)
            if not name.startswith('_') and callable(getattr(cls, name))
        }

    def test_base_agent_has_required_methods(self):
        """验证 BaseAgent 定义了必要方法"""
        required = {'prepare', 'execute', 'initialize'}
        base_methods = self.get_public_methods(BaseAgent)

        for method in required:
            assert method in base_methods, f"BaseAgent 缺少方法: {method}"

    def test_agent_result_has_required_fields(self):
        """验证 AgentResult 有必要字段"""
        # dataclass 的字段在 __dataclass_fields__ 中定义
        fields = getattr(AgentResult, '__dataclass_fields__', {})
        assert 'success' in fields, "AgentResult 缺少 success 字段"
        assert 'output' in fields, "AgentResult 缺少 output 字段"
        assert 'error' in fields, "AgentResult 缺少 error 字段"


class MockAgentForTest:
    """测试用 Mock Agent - 实现 BaseAgent 接口"""

    async def prepare(self, issue_id: str, context: dict) -> Workspace:
        return Workspace(
            id=issue_id,
            ready=True,
            workspace_path=str(Path.home() / f".swallowloop/default/{issue_id}/stages"),
            repo_url="",
            branch=issue_id,
            metadata={},
        )

    async def execute(self, task: str, context: dict) -> AgentResult:
        return AgentResult(success=True, output="mock output", error=None)

    async def initialize(self) -> None:
        pass


class TestExecutorWithInterface:
    """使用接口测试 ExecutorService"""

    def test_executor_accepts_any_agent_implementation(self):
        """验证 ExecutorService 接受任何 BaseAgent 实现"""

        class MockRepo:
            def __init__(self):
                self._issues = {}

            def save(self, issue):
                self._issues[str(issue.id)] = issue

            def get(self, issue_id):
                return self._issues.get(str(issue_id))

        repo = MockRepo()
        agent = MockAgentForTest()  # 任何实现 BaseAgent 的类

        # ExecutorService 应该接受任何 BaseAgent 实现
        executor = ExecutorService(
            repository=repo,
            agent=agent,
            agent_type="mock",
        )

        assert executor._agent is agent
