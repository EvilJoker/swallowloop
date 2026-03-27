"""Issue 模型模块测试"""

import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus, TodoItem, TodoStatus, Workspace


class TestIssueWorkspace:
    """Workspace 测试"""

    def test_workspace_creation(self):
        """测试 Workspace 创建"""
        workspace = Workspace(
            id="test-issue",
            ready=True,
            workspace_path="/path/to/workspace",
            repo_url="https://github.com/test/repo",
            branch="test-issue",
            metadata={"key": "value"},
        )

        assert workspace.id == "test-issue"
        assert workspace.ready is True
        assert workspace.workspace_path == "/path/to/workspace"
        assert workspace.repo_url == "https://github.com/test/repo"
        assert workspace.branch == "test-issue"
        assert workspace.metadata == {"key": "value"}

    def test_workspace_default_values(self):
        """测试 Workspace 默认值"""
        workspace = Workspace()

        assert workspace.id == ""
        assert workspace.ready is False
        assert workspace.workspace_path == ""
        assert workspace.repo_url == ""
        assert workspace.branch == ""
        assert workspace.metadata == {}


class TestIssue:
    """Issue 聚合根功能测试"""

    def test_issue_creation(self):
        """测试 Issue 创建"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="测试描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )

        assert issue.title == "测试"
        assert issue.description == "测试描述"
        assert issue.status == IssueStatus.ACTIVE
        assert issue.current_stage == Stage.BRAINSTORM
        assert issue.is_active is True

    def test_initial_stages_status(self):
        """初始所有阶段都是 NEW"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="测试描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )

        for stage in Stage:
            assert issue.get_stage_state(stage).status == StageStatus.NEW

    def test_todo_item(self):
        """测试 TodoItem"""
        todo = TodoItem(id="t1", content="任务1")
        assert todo.status == TodoStatus.PENDING

        todo.mark_in_progress()
        assert todo.status == TodoStatus.IN_PROGRESS

        todo.mark_completed()
        assert todo.status == TodoStatus.COMPLETED

        todo2 = TodoItem(id="t2", content="任务2")
        todo2.mark_failed()
        assert todo2.status == TodoStatus.FAILED

    def test_issue_archive(self):
        """测试 Issue 归档"""
        issue = Issue(
            id=IssueId("test-issue"),
            title="测试",
            description="测试描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )

        issue.status = IssueStatus.ARCHIVED
        issue.archived_at = datetime.now()

        assert issue.status == IssueStatus.ARCHIVED
        assert issue.is_active is False
