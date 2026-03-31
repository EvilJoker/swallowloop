"""Clean Service 模块测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from swallowloop.application.service.clean_service import CleanService
from swallowloop.domain.model import Issue, IssueId, Stage, IssueStatus, Workspace


class TestCleanService:
    """CleanService 功能测试"""

    @pytest.fixture
    def mock_repository(self):
        """创建模拟仓库"""
        repo = MagicMock()
        repo.list_all = MagicMock(return_value=[])
        repo.save = MagicMock()
        return repo

    @pytest.mark.asyncio
    async def test_should_cleanup_archived_issue(self, mock_repository):
        """测试应清理已归档的 Issue"""
        issue = Issue(
            id=IssueId("test-clean"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=False,
            cleaned_at=None,
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        should_clean = service._should_cleanup(issue)
        assert should_clean is True

    @pytest.mark.asyncio
    async def test_should_not_cleanup_active_issue(self, mock_repository):
        """测试不应清理活跃的 Issue"""
        issue = Issue(
            id=IssueId("test-active"),
            title="测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            cleaned=False,
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        should_clean = service._should_cleanup(issue)
        assert should_clean is False

    @pytest.mark.asyncio
    async def test_should_not_cleanup_already_cleaned_issue(self, mock_repository):
        """测试不应清理已清理过的 Issue"""
        issue = Issue(
            id=IssueId("test-cleaned"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=True,
            cleaned_at=datetime.now(),
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        should_clean = service._should_cleanup(issue)
        assert should_clean is False

    @pytest.mark.asyncio
    async def test_should_not_cleanup_within_interval(self, mock_repository):
        """测试清理间隔内不应再次清理"""
        issue = Issue(
            id=IssueId("test-interval"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=True,
            cleaned_at=datetime.now() - timedelta(minutes=30),  # 30分钟前清理
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        should_clean = service._should_cleanup(issue)
        assert should_clean is False

    @pytest.mark.asyncio
    async def test_should_cleanup_after_interval(self, mock_repository):
        """测试超过清理间隔后应清理"""
        issue = Issue(
            id=IssueId("test-past-interval"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=True,
            cleaned_at=datetime.now() - timedelta(hours=2),  # 2小时前清理
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        should_clean = service._should_cleanup(issue)
        assert should_clean is False  # 因为 cleaned=True

        # 测试 cleaned=False 但已过1小时
        issue2 = Issue(
            id=IssueId("test-past-interval-2"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now() - timedelta(hours=2),
            cleaned=False,
            cleaned_at=None,
        )

        should_clean2 = service._should_cleanup(issue2)
        assert should_clean2 is True

    @pytest.mark.asyncio
    async def test_cleanup_discarded_issue(self, mock_repository):
        """测试应清理已废弃的 Issue"""
        issue = Issue(
            id=IssueId("test-discarded"),
            title="测试",
            description="",
            status=IssueStatus.DISCARDED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            discarded_at=datetime.now(),
            cleaned=False,
            cleaned_at=None,
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        should_clean = service._should_cleanup(issue)
        assert should_clean is True

    @pytest.mark.asyncio
    async def test_cleanup_calls_deerflow_api(self, mock_repository):
        """测试清理调用 DeerFlow API"""
        issue = Issue(
            id=IssueId("test-api-call"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=False,
            cleaned_at=None,
            thread_id="test-api-call",
            thread_path="/home/user/.deer-flow/.deer-flow/threads/test-api-call/user-data/workspace",
        )

        mock_repository.list_all.return_value = [issue]

        mock_response = MagicMock()
        mock_response.status_code = 200

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        with patch.object(service._client, 'delete', new_callable=AsyncMock) as mock_delete:
            with patch('shutil.rmtree') as mock_rmtree:
                mock_delete.return_value = mock_response

                await service._cleanup_issue(issue)

                # 验证调用了 DELETE API
                mock_delete.assert_called_once_with("http://localhost:2024/threads/test-api-call")

                # 验证标记为已清理
                assert issue.cleaned is True
                assert issue.cleaned_at is not None
                mock_repository.save.assert_called_once_with(issue)

    @pytest.mark.asyncio
    async def test_cleanup_without_workspace_skips(self, mock_repository):
        """测试无 workspace 的 Issue 跳过清理"""
        issue = Issue(
            id=IssueId("test-no-workspace"),
            title="测试",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
            cleaned=False,
            cleaned_at=None,
            workspace=None,
        )

        mock_repository.list_all.return_value = [issue]

        service = CleanService(repository=mock_repository, base_url="http://localhost:2024")

        with patch.object(service._client, 'delete', new_callable=AsyncMock) as mock_delete:
            await service._cleanup_issue(issue)

            # 不应调用 DELETE API
            mock_delete.assert_not_called()
