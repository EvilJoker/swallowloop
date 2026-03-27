"""InMemory Issue Repository 模块测试"""

import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus, Workspace
from swallowloop.infrastructure.persistence import InMemoryIssueRepository


@pytest.fixture
def repo():
    """创建仓库实例"""
    return InMemoryIssueRepository()


class TestInMemoryIssueRepository:
    """InMemoryIssueRepository 功能测试"""

    def test_save_and_retrieve(self, repo):
        """测试保存和检索"""
        issue = Issue(
            id=IssueId("test-1"),
            title="测试",
            description="测试描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        retrieved = repo.get(IssueId("test-1"))
        assert retrieved is not None
        assert retrieved.title == "测试"
        assert retrieved.description == "测试描述"

    def test_get_nonexistent(self, repo):
        """测试获取不存在的 Issue"""
        retrieved = repo.get(IssueId("nonexistent"))
        assert retrieved is None

    def test_list_all(self, repo):
        """测试列出所有 Issue"""
        issue1 = Issue(
            id=IssueId("issue-1"),
            title="Issue 1",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue2 = Issue(
            id=IssueId("issue-2"),
            title="Issue 2",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue1)
        repo.save(issue2)

        all_issues = repo.list_all()
        assert len(all_issues) == 2

    def test_list_active(self, repo):
        """测试列出活跃 Issue"""
        active_issue = Issue(
            id=IssueId("active-issue"),
            title="活跃 Issue",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        archived_issue = Issue(
            id=IssueId("archived-issue"),
            title="已归档 Issue",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
        )
        repo.save(active_issue)
        repo.save(archived_issue)

        active_issues = repo.list_active()
        assert len(active_issues) == 1
        assert active_issues[0].id == IssueId("active-issue")

    def test_delete(self, repo):
        """测试删除 Issue"""
        issue = Issue(
            id=IssueId("to-delete"),
            title="待删除",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        success = repo.delete(IssueId("to-delete"))
        assert success is True

        retrieved = repo.get(IssueId("to-delete"))
        assert retrieved is None

    def test_delete_nonexistent(self, repo):
        """测试删除不存在的 Issue"""
        success = repo.delete(IssueId("nonexistent"))
        assert success is False

    def test_save_updates_existing(self, repo):
        """测试保存更新现有 Issue"""
        issue = Issue(
            id=IssueId("update-test"),
            title="原始标题",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        # 获取并修改
        retrieved = repo.get(IssueId("update-test"))
        retrieved.title = "新标题"
        repo.save(retrieved)

        # 验证已更新
        updated = repo.get(IssueId("update-test"))
        assert updated.title == "新标题"

    def test_workspace_persistence(self, repo):
        """测试 Workspace 持久化"""
        issue = Issue(
            id=IssueId("workspace-test"),
            title="Workspace 测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            workspace=Workspace(
                id="workspace-test",
                ready=True,
                workspace_path="/home/user/.deer-flow/threads/workspace-test/user-data/workspace",
                repo_url="https://github.com/test/repo",
                branch="workspace-test",
                metadata={"key": "value"},
            ),
            repo_url="https://github.com/test/repo",
        )
        repo.save(issue)

        retrieved = repo.get(IssueId("workspace-test"))
        assert retrieved.workspace is not None
        assert retrieved.workspace.id == "workspace-test"
        assert retrieved.workspace.ready is True
        assert retrieved.workspace.workspace_path == "/home/user/.deer-flow/threads/workspace-test/user-data/workspace"
        assert retrieved.workspace.repo_url == "https://github.com/test/repo"
        assert retrieved.workspace.branch == "workspace-test"
        assert retrieved.workspace.metadata == {"key": "value"}

    def test_cleanup_status_persistence(self, repo):
        """测试清理状态持久化"""
        issue = Issue(
            id=IssueId("cleanup-test"),
            title="清理测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=True,
            cleaned_at=datetime.now(),
        )
        repo.save(issue)

        retrieved = repo.get(IssueId("cleanup-test"))
        assert retrieved.cleaned is True
        assert retrieved.cleaned_at is not None
        assert retrieved.status == IssueStatus.ARCHIVED

    def test_list_stages_by_status(self, repo):
        """测试按状态列出阶段"""
        issue1 = Issue(
            id=IssueId("running-issue"),
            title="运行中 Issue",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        issue2 = Issue(
            id=IssueId("pending-issue"),
            title="待处理 Issue",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue1)
        repo.save(issue2)

        # 设置 issue1 的 brainstorm 为 RUNNING
        issue1.get_stage_state(Stage.BRAINSTORM).status = StageStatus.RUNNING
        repo.save(issue1)

        # 设置 issue2 的 brainstorm 为 PENDING
        issue2.get_stage_state(Stage.BRAINSTORM).status = StageStatus.PENDING
        repo.save(issue2)

        running_stages = repo.list_stages_by_status(StageStatus.RUNNING)
        assert len(running_stages) == 1
        assert running_stages[0][0].id == IssueId("running-issue")

        pending_stages = repo.list_stages_by_status(StageStatus.PENDING)
        assert len(pending_stages) == 1
        assert pending_stages[0][0].id == IssueId("pending-issue")
