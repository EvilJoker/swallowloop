"""Settings 模块测试"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from swallowloop.infrastructure.config import Settings


class TestSettings:
    """Settings 功能测试"""

    def test_default_values(self):
        """测试默认值"""
        settings = Settings(
            github_repo="owner/repo",
            github_repos=["owner/repo1", "owner/repo2"],
        )
        assert settings.github_repo == "owner/repo"
        assert settings.github_repos == ["owner/repo1", "owner/repo2"]
        assert settings.max_workers == 5
        assert settings.agent_timeout == 1200
        assert settings.poll_interval == 60
        assert settings.issue_label == "swallow"
        assert settings.base_branch == "main"
        assert settings.log_level == "INFO"
        assert settings.web_enabled is True
        assert settings.web_port == 8080
        assert settings.agent_type == "mock"

    def test_custom_values(self):
        """测试自定义值"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
            max_workers=10,
            agent_timeout=600,
            web_port=9000,
        )
        assert settings.max_workers == 10
        assert settings.agent_timeout == 600
        assert settings.web_port == 9000

    def test_workspaces_dir(self):
        """工作空间目录"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
        )
        expected = Path.home() / ".swallowloop" / "workspaces"
        assert settings.workspaces_dir == expected

    def test_workspaces_dir_custom_work_dir(self):
        """自定义工作目录"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
            work_dir=Path("/custom/path"),
        )
        assert settings.workspaces_dir == Path("/custom/path/workspaces")

    def test_data_dir(self):
        """数据目录"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
        )
        expected = Path.home() / ".swallowloop"
        assert settings.data_dir == expected

    def test_logs_dir(self):
        """日志目录"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
        )
        expected = Path.home() / ".swallowloop" / "logs"
        assert settings.logs_dir == expected

    def test_logs_dir_custom_log_dir(self):
        """自定义日志目录"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
            log_dir=Path("/var/log/swallow"),
        )
        assert settings.logs_dir == Path("/var/log/swallow")

    @patch.dict(os.environ, {
        "REPOS": "env/repo1, env/repo2, env/repo3",
        "MAX_WORKERS": "3",
        "AGENT_TYPE": "deerflow",
    })
    def test_from_env(self):
        """从环境变量加载配置"""
        settings = Settings.from_env()

        assert settings.github_repos == ["env/repo1", "env/repo2", "env/repo3"]
        assert settings.max_workers == 3
        assert settings.agent_type == "deerflow"

    @patch.dict(os.environ, {
        "REPOS": "owner/repo1, owner/repo2, owner/repo3",
    })
    def test_from_env_multi_repos(self):
        """多仓库配置"""
        settings = Settings.from_env()

        assert settings.github_repos == ["owner/repo1", "owner/repo2", "owner/repo3"]

    @patch.dict(os.environ, {
        "REPOS": "",
    })
    def test_from_env_no_repos(self):
        """无仓库配置"""
        settings = Settings.from_env()

        assert settings.github_repos == []

    @patch.dict(os.environ, {
        "REPOS": "owner/repo",
    })
    def test_from_env_single_repo_fallback(self):
        """单仓库回退"""
        settings = Settings.from_env()

        assert settings.github_repos == ["owner/repo"]

    def test_get_llm_config_default(self):
        """获取默认 LLM 配置"""
        settings = Settings(
            github_repo="a/b",
            github_repos=["a/b"],
        )
        # llm_config 为 None 时，返回默认配置（OpenAI）
        llm = settings.get_llm_config()
        assert llm.provider.value == "openai"

    @patch.dict(os.environ, {
        "REPOS": "owner/repo",
        "LLM_PROVIDER": "openai",
        "LLM_API_KEY": "sk-test",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL_NAME": "gpt-4o",
    })
    def test_from_env_with_llm_config(self):
        """带 LLM 配置的环境变量"""
        settings = Settings.from_env()

        assert settings.llm_config is not None
        assert settings.llm_config.provider.value == "openai"
        assert settings.llm_config.api_key == "sk-test"
