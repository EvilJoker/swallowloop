"""Config 模块测试"""

import os
import pytest
from pathlib import Path
from swallowloop.infrastructure.config import Config


class TestConfigLoad:
    """Config.load() 加载测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        Config._instance = None
        Config._loaded = False

    def test_load_from_empty_dir(self, tmp_path):
        """空目录加载"""
        config = Config.load(config_dir=tmp_path)
        assert config is not None
        assert Config.is_loaded()

    def test_load_env_file(self, tmp_path):
        """加载 .env 文件"""
        env_file = tmp_path / ".env"
        env_file.write_text("REPOS=owner/repo\n")

        config = Config.load(config_dir=tmp_path)

        assert config.get("REPOS") == "owner/repo"

    def test_env_vars_override_dotenv(self, tmp_path):
        """环境变量覆盖 .env 同名配置"""
        env_file = tmp_path / ".env"
        env_file.write_text("REPOS=dotenv_repo\n")

        config = Config.load(config_dir=tmp_path)
        # 此时没有同名环境变量，应该用 .env 的值
        assert config.get("REPOS") == "dotenv_repo"

    def test_load_yaml_file(self, tmp_path):
        """加载 config.yaml"""
        env_file = tmp_path / ".env"
        env_file.write_text("REPOS=owner/repo\n")

        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("agent_type: deerflow\npoll_interval: 30\n")

        config = Config.load(config_dir=tmp_path)

        assert config.get("AGENT_TYPE") == "deerflow"
        assert config.get("REPOS") == "owner/repo"
        # YAML 数字会被解析为 int
        assert config.get("POLL_INTERVAL") == 30

    def test_yaml_var_substitution(self, tmp_path):
        """${} 变量替换"""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("llm_api_key: ${API_KEY}\n")

        config = Config.load(config_dir=tmp_path)

        assert config.get("LLM_API_KEY") == "secret123"

    def test_yaml_var_with_default(self, tmp_path):
        """${VAR:default} 默认值"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("missing_var: ${NOT_EXIST:default_value}\n")

        config = Config.load(config_dir=tmp_path)

        assert config.get("MISSING_VAR") == "default_value"

    def test_nested_yaml_keys(self, tmp_path):
        """嵌套 YAML keys 转为大写下划线"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""
server:
  host: localhost
  port: 8080
""")

        config = Config.load(config_dir=tmp_path)

        assert config.get("SERVER_HOST") == "localhost"
        assert config.get("SERVER_PORT") == 8080  # YAML 解析为 int

    def test_priority_env_over_dotenv(self, tmp_path):
        """环境变量优先级高于 .env"""
        env_file = tmp_path / ".env"
        env_file.write_text("REPOS=dotenv_repo\n")

        # 通过环境变量覆盖
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("REPOS", "env_repo")
            config = Config.load(config_dir=tmp_path)

        assert config.get("REPOS") == "env_repo"


class TestConfigGet:
    """Config.get() 和 get_xxx() 方法测试"""

    def setup_method(self):
        Config._instance = None
        Config._loaded = False

    def test_get_with_default(self, tmp_path):
        """默认值测试"""
        config = Config.load(config_dir=tmp_path)
        assert config.get("NOT_EXIST", "default") == "default"

    def test_get_case_insensitive(self, tmp_path):
        """key 不区分大小写"""
        env_file = tmp_path / ".env"
        env_file.write_text("test_key=value\n")

        config = Config.load(config_dir=tmp_path)

        assert config.get("TEST_KEY") == "value"
        assert config.get("test_key") == "value"
        assert config.get("Test_Key") == "value"

    def test_get_github_repos(self, tmp_path):
        """get_github_repos()"""
        env_file = tmp_path / ".env"
        env_file.write_text("REPOS=owner/repo1,owner/repo2,owner/repo3\n")

        config = Config.load(config_dir=tmp_path)

        assert config.get_github_repos() == ["owner/repo1", "owner/repo2", "owner/repo3"]

    def test_get_github_repos_empty(self, tmp_path):
        """get_github_repos() 空值"""
        config = Config.load(config_dir=tmp_path)
        assert config.get_github_repos() == []

    def test_get_agent_type(self, tmp_path):
        """get_agent_type()"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("agent_type: deerflow\n")

        config = Config.load(config_dir=tmp_path)
        assert config.get_agent_type() == "deerflow"

    def test_get_agent_type_default(self, tmp_path):
        """get_agent_type() 默认值"""
        config = Config.load(config_dir=tmp_path)
        assert config.get_agent_type() == "mock"

    def test_get_deerflow_base_url(self, tmp_path):
        """get_deerflow_base_url()"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("deerflow_base_url: http://localhost:2026\n")

        config = Config.load(config_dir=tmp_path)
        assert config.get_deerflow_base_url() == "http://localhost:2026"

    def test_get_poll_interval(self, tmp_path):
        """get_poll_interval()"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("poll_interval: 30\n")

        config = Config.load(config_dir=tmp_path)
        assert config.get_poll_interval() == 30

    def test_get_max_workers(self, tmp_path):
        """get_max_workers()"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("max_workers: 10\n")

        config = Config.load(config_dir=tmp_path)
        assert config.get_max_workers() == 10

    def test_get_llm_config(self, tmp_path):
        """get_llm_config()"""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=secret\n")

        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""
llm_provider: minimax
llm_base_url: https://api.minimaxi.com/v1
llm_model_name: m2.7
""")

        config = Config.load(config_dir=tmp_path)
        llm = config.get_llm_config()

        assert llm["provider"] == "minimax"
        assert llm["api_key"] == "secret"
        assert llm["base_url"] == "https://api.minimaxi.com/v1"
        assert llm["model_name"] == "m2.7"

    def test_get_work_dir(self, tmp_path):
        """get_work_dir()"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("work_dir: /custom/path\n")

        config = Config.load(config_dir=tmp_path)
        assert config.get_work_dir() == Path("/custom/path")

    def test_workspaces_dir(self, tmp_path):
        """workspaces_dir 属性"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("work_dir: /custom/path\n")

        config = Config.load(config_dir=tmp_path)
        assert config.workspaces_dir == Path("/custom/path/workspaces")

    def test_data_dir(self, tmp_path):
        """data_dir 属性（默认 ~/.swallowloop）"""
        config = Config.load(config_dir=tmp_path)
        # data_dir 默认返回 ~/.swallowloop
        assert config.data_dir == Path.home() / ".swallowloop"

    def test_logs_dir(self, tmp_path):
        """logs_dir 属性"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("log_dir: /var/logs\n")

        config = Config.load(config_dir=tmp_path)
        assert config.logs_dir == Path("/var/logs")


class TestConfigSingleton:
    """单例模式测试"""

    def setup_method(self):
        Config._instance = None
        Config._loaded = False

    def test_singleton(self, tmp_path):
        """单例模式"""
        config1 = Config.load(config_dir=tmp_path)
        config2 = Config.load(config_dir=tmp_path)

        assert config1 is config2
        assert Config.get_instance() is config1

    def test_get_instance_before_load(self):
        """load 前调用 get_instance 抛出异常"""
        Config._instance = None
        Config._loaded = False

        with pytest.raises(RuntimeError, match="未加载"):
            Config.get_instance()

    def test_is_loaded(self, tmp_path):
        """is_loaded()"""
        assert not Config.is_loaded()
        Config.load(config_dir=tmp_path)
        assert Config.is_loaded()
