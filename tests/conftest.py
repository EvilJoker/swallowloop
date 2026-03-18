"""
端到端测试配置和共享 fixtures

提供测试所需的 Mock 组件，用于隔离外部依赖
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Union
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field

import pytest

# 添加 src 到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from swallowloop.domain.model import Task, TaskId, TaskType, Workspace, Comment, PullRequest
from swallowloop.domain.model.enums import TaskState
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from swallowloop.infrastructure.source_control.base import IssueInfo, PullRequestInfo, CommentInfo
from swallowloop.infrastructure.agent.base import Agent, ExecutionResult
from swallowloop.infrastructure.persistence import JsonTaskRepository, JsonWorkspaceRepository
from swallowloop.application.dto import IssueDTO


# ==================== Mock 数据类 ====================

@dataclass
class MockIssue:
    """模拟 Issue 数据"""
    number: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = field(default_factory=lambda: ["swallow"])
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MockPR:
    """模拟 PR 数据"""
    number: int
    html_url: str
    branch_name: str
    title: str
    body: str = ""
    state: str = "open"
    merged: bool = False


# ==================== Mock Source Control ====================

class MockSourceControl:
    """
    模拟源码控制系统
    
    用于测试时不依赖真实 GitHub API
    """
    
    def __init__(self):
        self._issues: dict[int, Union[MockIssue, IssueDTO]] = {}
        self._prs: dict[int, MockPR] = {}
        self._comments: dict[int, list[CommentInfo]] = {}
        self._branches: set[str] = set()
        self._comment_counter = 0
        self._pr_counter = 0
        self._clone_url = "https://token@github.com/test/repo.git"
        self._created_prs: list[dict] = []
        
    def reset(self):
        """重置所有状态"""
        self._issues.clear()
        self._prs.clear()
        self._comments.clear()
        self._branches.clear()
        self._comment_counter = 0
        self._pr_counter = 0
        self._created_prs.clear()
    
    # ==================== 设置测试数据 ====================
    
    def add_issue(self, issue: Union[MockIssue, IssueDTO, "IssueInfo"]) -> None:
        """添加 Issue（支持多种类型）"""
        self._issues[issue.number] = issue
        self._comments[issue.number] = []
    
    def remove_issue(self, issue_number: int) -> None:
        """移除/关闭 Issue"""
        if issue_number in self._issues:
            self._issues[issue_number].state = "closed"
    
    def add_comment(self, issue_number: int, body: str, author: str = "user") -> int:
        """添加评论，返回评论ID"""
        self._comment_counter += 1
        comment = CommentInfo(
            id=self._comment_counter,
            body=body,
            author=author,
            created_at=datetime.now(),
        )
        if issue_number not in self._comments:
            self._comments[issue_number] = []
        self._comments[issue_number].append(comment)
        return self._comment_counter
    
    def add_comment_object(self, issue_number: int, comment: Comment) -> int:
        """添加 Comment 对象"""
        self._comment_counter += 1
        comment_info = CommentInfo(
            id=comment.id,
            body=comment.body,
            author=comment.author,
            created_at=comment.created_at,
        )
        if issue_number not in self._comments:
            self._comments[issue_number] = []
        self._comments[issue_number].append(comment_info)
        return self._comment_counter
    
    def close_issue(self, issue_number: int) -> None:
        """关闭 Issue"""
        if issue_number in self._issues:
            self._issues[issue_number].state = "closed"
    
    def merge_pr(self, pr_number: int) -> None:
        """合并 PR"""
        if pr_number in self._prs:
            self._prs[pr_number].merged = True
            self._prs[pr_number].state = "closed"
    
    def add_branch(self, branch_name: str) -> None:
        """添加分支"""
        self._branches.add(branch_name)
    
    # ==================== 辅助方法 ====================
    
    def _get_issue_state(self, issue) -> str:
        """获取 Issue 的状态"""
        return getattr(issue, 'state', 'open')
    
    def _get_issue_labels(self, issue) -> list[str]:
        """获取 Issue 的标签"""
        labels = getattr(issue, 'labels', [])
        if labels and not isinstance(labels[0], str):
            # 如果 labels 是对象列表（如 PyGithub 的 Label 对象）
            return [l.name if hasattr(l, 'name') else str(l) for l in labels]
        return list(labels) if labels else []
    
    # ==================== 实现 SourceControl 接口 ====================
    
    def get_labeled_issues(self, label: str) -> list[IssueInfo]:
        """获取带标签的 Issue"""
        result = []
        for issue in self._issues.values():
            issue_state = self._get_issue_state(issue)
            issue_labels = self._get_issue_labels(issue)
            
            if label in issue_labels and issue_state == "open":
                result.append(IssueInfo(
                    number=issue.number,
                    title=issue.title,
                    body=issue.body or "",
                    state=issue_state,
                    labels=issue_labels,
                    created_at=getattr(issue, 'created_at', datetime.now()),
                    updated_at=getattr(issue, 'updated_at', datetime.now()),
                ))
        return result
    
    def get_issue(self, issue_number: int) -> IssueInfo:
        """获取 Issue"""
        issue = self._issues.get(issue_number)
        if not issue:
            raise ValueError(f"Issue #{issue_number} 不存在")
        return IssueInfo(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=self._get_issue_state(issue),
            labels=self._get_issue_labels(issue),
            created_at=getattr(issue, 'created_at', datetime.now()),
            updated_at=getattr(issue, 'updated_at', datetime.now()),
        )
    
    def get_issue_comments(self, issue_number: int) -> list[Comment]:
        """获取 Issue 评论（返回 Comment 对象）"""
        comments = []
        for c in self._comments.get(issue_number, []):
            comments.append(Comment(
                id=c.id,
                body=c.body,
                author=c.author,
                created_at=c.created_at,
            ))
        return comments
    
    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PullRequestInfo:
        """创建 PR"""
        self._pr_counter += 1
        pr = MockPR(
            number=self._pr_counter,
            html_url=f"https://github.com/test/repo/pull/{self._pr_counter}",
            branch_name=branch_name,
            title=title,
            body=body,
        )
        self._prs[pr.number] = pr
        self._branches.add(branch_name)
        
        self._created_prs.append({
            "number": pr.number,
            "branch_name": branch_name,
            "title": title,
            "body": body,
        })
        
        return PullRequestInfo(
            number=pr.number,
            html_url=pr.html_url,
            branch_name=pr.branch_name,
            title=pr.title,
            body=pr.body,
            state=pr.state,
            merged=pr.merged,
        )
    
    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """获取 PR"""
        pr = self._prs.get(pr_number)
        if not pr:
            raise ValueError(f"PR #{pr_number} 不存在")
        return PullRequestInfo(
            number=pr.number,
            html_url=pr.html_url,
            branch_name=pr.branch_name,
            title=pr.title,
            body=pr.body,
            state=pr.state,
            merged=pr.merged,
        )
    
    def comment_on_issue(self, issue_number: int, body: str) -> None:
        """在 Issue 上评论"""
        self.add_comment(issue_number, body, author="swallowloop-bot")
    
    def has_branch(self, branch_name: str) -> bool:
        """检查分支是否存在"""
        return branch_name in self._branches
    
    def get_clone_url_with_token(self) -> str:
        """获取克隆 URL"""
        return self._clone_url
    
    def get_clone_url(self) -> str:
        """获取克隆 URL（不带 token）"""
        return "https://github.com/test/repo.git"
    
    @property
    def provider_name(self) -> str:
        return "mock"


# ==================== Mock Agent ====================

class MockAgent(Agent):
    """
    模拟 Agent
    
    模拟代码生成过程，不实际执行
    """
    
    def __init__(self):
        self._execution_count = 0
        self._should_succeed = True
        self._files_to_change: list[str] = []
        self._execution_delay: float = 0.0
        self._last_task: Task | None = None
        self._last_workspace: Path | None = None
    
    def reset(self):
        """重置状态"""
        self._execution_count = 0
        self._should_succeed = True
        self._files_to_change = []
        self._execution_delay = 0.0
        self._last_task = None
        self._last_workspace = None
    
    def set_success(self, should_succeed: bool) -> None:
        """设置是否成功"""
        self._should_succeed = should_succeed
    
    def set_files_to_change(self, files: list[str]) -> None:
        """设置要修改的文件"""
        self._files_to_change = files
    
    def set_execution_delay(self, delay: float) -> None:
        """设置执行延迟（秒）"""
        self._execution_delay = delay
    
    @property
    def name(self) -> str:
        return "mock"
    
    @property
    def execution_count(self) -> int:
        return self._execution_count
    
    @property
    def last_task(self) -> Task | None:
        return self._last_task
    
    @property
    def last_workspace(self) -> Path | None:
        return self._last_workspace
    
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """执行任务"""
        import time
        
        self._execution_count += 1
        self._last_task = task
        self._last_workspace = workspace_path
        
        if self._execution_delay > 0:
            time.sleep(self._execution_delay)
        
        if self._should_succeed:
            # 模拟文件修改
            for file_path in self._files_to_change:
                full_path = workspace_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(f"// Modified by MockAgent for Issue#{task.issue_number}")
            
            return ExecutionResult(
                success=True,
                message="执行成功",
                files_changed=self._files_to_change,
            )
        else:
            return ExecutionResult(
                success=False,
                message="模拟执行失败",
            )
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        return True, "MockAgent 就绪"


# ==================== Fixtures ====================

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_source_control():
    """创建模拟源码控制"""
    return MockSourceControl()


@pytest.fixture
def mock_agent():
    """创建模拟 Agent"""
    return MockAgent()


@pytest.fixture
def task_repository(temp_dir: Path) -> TaskRepository:
    """创建任务仓库"""
    return JsonTaskRepository(temp_dir)


@pytest.fixture
def workspace_repository(temp_dir: Path) -> WorkspaceRepository:
    """创建工作空间仓库"""
    return JsonWorkspaceRepository(temp_dir)


@pytest.fixture
def test_settings(temp_dir):
    """创建测试配置"""
    from swallowloop.infrastructure.config import Settings
    
    return Settings(
        github_token="test_token",
        github_repo="test/repo",
        llm_model="gpt-4o",
        agent_type="mock",
        agent_timeout=60,
        work_dir=temp_dir,
        poll_interval=1,
        issue_label="swallow",
        base_branch="main",
    )


@pytest.fixture
def sample_issue() -> IssueDTO:
    """创建示例 Issue DTO"""
    return IssueDTO(
        number=1,
        title="修复登录页面的按钮样式问题",
        body="登录按钮在移动端显示不正确，需要调整 CSS 样式。",
        state="open",
        labels=["swallow"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_revision_issue() -> IssueDTO:
    """创建需要修改的 Issue DTO"""
    return IssueDTO(
        number=2,
        title="添加用户注册功能",
        body="需要实现用户注册表单和验证逻辑。",
        state="open",
        labels=["swallow"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_task(temp_dir: Path) -> Task:
    """创建示例任务"""
    return Task(
        task_id=TaskId("task-1"),
        issue_number=1,
        title="修复登录页面的按钮样式问题",
        description="登录按钮在移动端显示不正确，需要调整 CSS 样式。",
        branch_name="Issue1_fix-login-button-style",
    )


@pytest.fixture
def sample_workspace(temp_dir: Path) -> Workspace:
    """创建示例工作空间"""
    workspace_path = temp_dir / "issue1_20260317"
    workspace_path.mkdir(parents=True, exist_ok=True)
    return Workspace(
        id="issue1_20260317",
        issue_number=1,
        branch_name="Issue1_fix-login-button-style",
        path=workspace_path,
    )


@pytest.fixture
def sample_comment() -> Comment:
    """创建示例评论"""
    return Comment(
        id=1,
        body="请也添加对应的单元测试用例。",
        author="reviewer",
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_pr() -> PullRequest:
    """创建示例 PR"""
    return PullRequest(
        number=101,
        html_url="https://github.com/test/repo/pull/101",
        branch_name="Issue1_fix-login-button-style",
        title="Issue#1: 修复登录页面的按钮样式问题",
    )


# ==================== 并发测试 Fixtures ====================

class MockSlowAgent(MockAgent):
    """模拟慢速 Agent，用于并发测试"""
    
    def __init__(self, execution_delay: float = 2.0):
        super().__init__()
        self._execution_delay = execution_delay
        self._active_count = 0
        self._max_active_count = 0
    
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """执行任务，记录并发数"""
        import time
        
        self._active_count += 1
        self._max_active_count = max(self._max_active_count, self._active_count)
        
        try:
            if self._execution_delay > 0:
                time.sleep(self._execution_delay)
            
            return super().execute(task, workspace_path)
        finally:
            self._active_count -= 1
    
    @property
    def max_active_count(self) -> int:
        return self._max_active_count


@pytest.fixture
def mock_slow_agent():
    """创建模拟慢速 Agent"""
    return MockSlowAgent(execution_delay=0.5)


# ==================== Web Dashboard Fixtures ====================

@pytest.fixture
def mock_dashboard_app(temp_dir, mock_source_control, mock_agent):
    """创建测试用 Dashboard 应用"""
    from swallowloop.infrastructure.config import Settings
    from swallowloop.interfaces.web.dashboard import DashboardServer
    
    settings = Settings(
        github_token="test_token",
        github_repo="test/repo",
        work_dir=temp_dir,
    )
    
    task_repo = JsonTaskRepository(temp_dir)
    workspace_repo = JsonWorkspaceRepository(temp_dir)
    
    dashboard = DashboardServer(
        task_repository=task_repo,
        workspace_repository=workspace_repo,
        settings=settings,
        port=8765,  # 使用非标准端口避免冲突
    )
    
    return dashboard, task_repo, workspace_repo
