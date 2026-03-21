"""Self-update 模块测试"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from swallowloop.infrastructure.self_update import SelfUpdater


class TestSelfUpdaterCheckForUpdate:
    """测试 check_for_update 方法"""

    @pytest.fixture
    def mock_updater(self, tmp_path):
        """创建测试用的 SelfUpdater 实例"""
        with patch.object(SelfUpdater, "_find_repo_path", return_value=tmp_path):
            updater = SelfUpdater(repo_path=tmp_path, check_interval=0)
            updater._last_check_time = None  # 强制立即检查
            return updater

    def test_local_ahead_of_remote_should_not_update(self, mock_updater, tmp_path):
        """
        Bug: 本地领先远程时误报"发现新版本"

        当本地 commit > 远程 commit 时，不应该触发更新
        这是之前 commit af50e9e 修复的 bug
        """
        # 模拟 git log 输出为空（远程没有本地没有的 commit）
        with patch.object(
            mock_updater, "_get_current_commit", return_value="abc123"
        ), patch.object(
            mock_updater, "_get_remote_commit", return_value="def456"
        ), patch.object(
            subprocess, "run"
        ) as mock_run:
            # git log local..origin/main 返回空，说明远程没有本地没有的 commit
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            result = mock_updater.check_for_update()

            assert result is False, "本地领先时不应该触发更新"

    def test_remote_ahead_of_local_should_update(self, mock_updater, tmp_path):
        """远程领先本地时应该触发更新"""
        with patch.object(
            mock_updater, "_get_current_commit", return_value="abc123"
        ), patch.object(
            mock_updater, "_get_remote_commit", return_value="def456"
        ), patch.object(
            subprocess, "run"
        ) as mock_run:
            # git log local..origin/main 返回非空，说明远程有本地没有的 commit
            mock_run.return_value = MagicMock(
                stdout="commit1\ncommit2\ncommit3", stderr="", returncode=0
            )

            result = mock_updater.check_for_update()

            assert result is True, "远程领先时应该触发更新"

    def test_local_and_remote_in_sync_no_update(self, mock_updater, tmp_path):
        """本地和远程同步时不应该更新"""
        with patch.object(
            mock_updater, "_get_current_commit", return_value="abc123"
        ), patch.object(
            mock_updater, "_get_remote_commit", return_value="abc123"
        ), patch.object(
            subprocess, "run"
        ) as mock_run:
            # git log local..origin/main 返回空
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)

            result = mock_updater.check_for_update()

            assert result is False, "本地和远程同步时不应该更新"

    def test_git_command_error_should_not_crash(self, mock_updater, tmp_path):
        """git 命令执行失败时应该安全处理"""
        with patch.object(
            mock_updater, "_get_current_commit", return_value="abc123"
        ), patch.object(
            mock_updater, "_get_remote_commit", return_value="def456"
        ), patch.object(
            subprocess, "run"
        ) as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            result = mock_updater.check_for_update()

            # 应该返回 False 而不是崩溃
            assert result is False
