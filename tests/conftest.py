"""共享 fixtures"""

import pytest
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from tests.helpers import MockRepository, MockExecutor


@pytest.fixture
def mock_repo():
    """Mock 仓库"""
    return MockRepository()


@pytest.fixture
def mock_executor(mock_repo):
    """Mock 执行器"""
    return MockExecutor(repository=mock_repo)


@pytest.fixture
def sample_issue(mock_repo):
    """创建测试用 Issue"""
    issue = Issue(
        id=IssueId("test-issue"),
        title="测试",
        description="测试描述",
        status=IssueStatus.ACTIVE,
        current_stage=Stage.SPECIFY,
        created_at=datetime.now(),
    )
    mock_repo.save(issue)
    return issue
