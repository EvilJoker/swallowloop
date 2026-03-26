"""SelfUpdater 模块测试"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from swallowloop.infrastructure.self_update import SelfUpdater


class TestSelfUpdater:
    """SelfUpdater 功能测试"""

    def test_init_with_repo_path(self, tmp_path):
        """测试使用指定仓库路径初始化"""
        updater = SelfUpdater(repo_path=tmp_path, check_interval=60)
        assert updater._repo_path == tmp_path
        assert updater._check_interval == 60

    def test_should_check_initially(self, tmp_path):
        """初始检查应该返回 True"""
        updater = SelfUpdater(repo_path=tmp_path)
        assert updater.should_check() is True

    def test_should_not_check_within_interval(self, tmp_path):
        """检查间隔内不应再次检查"""
        from datetime import datetime
        updater = SelfUpdater(repo_path=tmp_path, check_interval=300)
        updater._last_check_time = datetime.now()
        assert updater.should_check() is False

    @patch("swallowloop.infrastructure.self_update.subprocess.run")
    def test_check_for_update_git_error(self, mock_run, tmp_path):
        """Git 命令错误时返回 False"""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        updater = SelfUpdater(repo_path=tmp_path)
        result = updater.check_for_update()
        assert result is False

    @patch("swallowloop.infrastructure.self_update.subprocess.run")
    def test_check_for_update_already_up_to_date(self, mock_run, tmp_path):
        """已是最新版本时不更新"""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        updater = SelfUpdater(repo_path=tmp_path)
        result = updater.check_for_update()
        assert result is False

    @patch("swallowloop.infrastructure.self_update.subprocess.run")
    def test_check_for_update_needs_update(self, mock_run, tmp_path):
        """远程有新版本时返回 True"""
        mock_run.return_value = MagicMock(
            stdout="commit1\ncommit2",
            returncode=0
        )
        updater = SelfUpdater(repo_path=tmp_path)
        result = updater.check_for_update()
        assert result is True
