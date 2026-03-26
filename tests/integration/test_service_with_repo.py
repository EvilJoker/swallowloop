"""Service + Repository 集成测试"""

import pytest
from swallowloop.application.service import IssueService
from swallowloop.infrastructure.persistence import InMemoryIssueRepository


@pytest.fixture
def repo():
    return InMemoryIssueRepository()


@pytest.fixture
def service(repo):
    from tests.helpers import MockExecutor
    executor = MockExecutor(repository=repo)
    return IssueService(repo, executor)


class TestServiceWithRepository:
    """Service 与 Repository 集成测试"""

    @pytest.mark.asyncio
    async def test_create_and_retrieve(self, repo, service):
        """创建后通过 repo 能正确检索"""
        issue = await service.create_issue("测试", "描述")
        retrieved = repo.get(issue.id)

        assert retrieved is not None
        assert retrieved.title == "测试"
        assert retrieved.id == issue.id

    @pytest.mark.asyncio
    async def test_update_persistence(self, repo, service):
        """更新后数据持久化"""
        issue = await service.create_issue("原始", "描述")
        issue_id = str(issue.id)

        service.update_issue(issue_id, title="更新后")

        retrieved = repo.get(issue.id)
        assert retrieved.title == "更新后"

    @pytest.mark.asyncio
    async def test_delete_persistence(self, repo, service):
        """删除后 repo 中不存在"""
        issue = await service.create_issue("测试", "描述")
        issue_id = str(issue.id)

        await service.delete_issue(issue_id)

        assert repo.get(issue.id) is None
