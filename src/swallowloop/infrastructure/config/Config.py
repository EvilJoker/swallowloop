"""SwallowLoop 配置管理 - 单例模式"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


class Config:
    """SwallowLoop 配置单例"""

    _instance: "Config | None" = None
    _loaded: bool = False

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._env_vars: dict[str, str] = {}

    # 默认 .env 模板
    DEFAULT_ENV_TEMPLATE = """# SwallowLoop 配置

# ============ 必需配置 ============

# GitHub Token
GITHUB_TOKEN=your_github_token_here

# 目标仓库 (owner/repo 格式，多个用逗号分隔)
GITHUB_REPO=owner/repo

# ============ LLM API 配置 ============

# LLM API Key
OPENAI_API_KEY=your_api_key_here

# LLM API 地址
OPENAI_API_BASE_URL=https://api.minimaxi.com/v1

# LLM 模型
LLM_MODEL=openai/MiniMax-M2.5-highspeed

# ============ Worker Agent 配置 ============

# Agent 类型 (mock: 模拟 Agent，deerflow: 使用 DeerFlow)
AGENT_TYPE=mock

# 最大 Worker 数量
MAX_WORKERS=5

# 轮询间隔 (秒)
POLL_INTERVAL=60

# 监听的 Issue 标签
ISSUE_LABEL=swallow

# 基础分支
BASE_BRANCH=main

# ============ DeerFlow 配置 ============

# DeerFlow API 地址
DEERFLOW_BASE_URL=http://localhost:2026
"""

    # 默认 config.yaml 模板
    DEFAULT_CONFIG_YAML = """# SwallowLoop 业务配置
# 此文件中的值可以使用 ${ENV_VAR} 引用环境变量

# 工作目录
work_dir: ~/.swallowloop

# 日志目录
log_dir: ~/.swallowloop/logs

# DeerFlow 配置
deerflow:
  base_url: ${DEERFLOW_BASE_URL:http://localhost:2026}
  data_dir: ~/.deer-flow

# Agent 配置
agent:
  type: ${AGENT_TYPE:mock}
  max_workers: ${MAX_WORKERS:5}

# GitHub 配置
github:
  repos: ${GITHUB_REPO:}
  issue_label: ${ISSUE_LABEL:swallow}
  base_branch: ${BASE_BRANCH:main}
"""

    @classmethod
    def load(cls, config_dir: Path | str | None = None) -> "Config":
        """
        加载配置（单例）

        加载顺序：
        1. ~/.swallowloop/.env → 敏感信息
        2. 环境变量 → 覆盖 .env 同名配置
        3. ~/.swallowloop/config.yaml → 业务配置，${} 替换

        如果配置文件不存在，会自动生成默认模板。

        Args:
            config_dir: 配置目录，默认为 ~/.swallowloop
        """
        if cls._instance is not None and cls._loaded:
            return cls._instance

        cls._instance = cls()
        instance = cls._instance

        # 确定配置目录
        if config_dir is None:
            config_dir = Path.home() / ".swallowloop"
        elif isinstance(config_dir, str):
            config_dir = Path(config_dir)

        # 确保配置目录存在
        config_dir.mkdir(parents=True, exist_ok=True)

        # 1. 加载或生成 .env 文件
        env_path = config_dir / ".env"
        if env_path.exists():
            instance._load_env_file(env_path)
        else:
            # 生成默认 .env 模板
            cls._generate_default_env(env_path)
            instance._load_env_file(env_path)

        # 2. 环境变量覆盖
        instance._merge_env_vars()

        # 3. 加载或生成 config.yaml
        yaml_path = config_dir / "config.yaml"
        if yaml_path.exists():
            instance._load_yaml(yaml_path)
        else:
            # 生成默认 config.yaml
            cls._generate_default_config_yaml(config_dir / "config.yaml")
            instance._load_yaml(yaml_path)

        cls._loaded = True
        return cls._instance

    @classmethod
    def _generate_default_env(cls, path: Path) -> None:
        """生成默认 .env 文件"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(cls.DEFAULT_ENV_TEMPLATE)

    @classmethod
    def _generate_default_config_yaml(cls, path: Path) -> None:
        """生成默认 config.yaml 文件"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(cls.DEFAULT_CONFIG_YAML)

    def _load_env_file(self, path: Path) -> None:
        """加载 .env 文件"""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 统一存储为大写 key
                    key_upper = key.upper()
                    self._env_vars[key_upper] = value
                    self._data[key_upper] = value

    def _merge_env_vars(self) -> None:
        """环境变量覆盖 .env 同名配置"""
        for key, value in os.environ.items():
            self._data[key] = value
            self._env_vars[key] = value

    def _load_yaml(self, path: Path) -> None:
        """加载 config.yaml，${} 替换变量"""
        with open(path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        if yaml_data:
            self._merge_yaml("", yaml_data)

    def _merge_yaml(self, prefix: str, data: dict | Any) -> None:
        """递归合并 yaml 数据，${} 替换变量"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{prefix}_{key}".upper() if prefix else key.upper()
                self._merge_yaml(new_key, value)
        elif isinstance(data, str):
            # 替换 ${VAR_NAME} 或 ${VAR_NAME:default}
            def replace_var(match):
                var_expr = match.group(1)
                if ":" in var_expr:
                    var_name, default = var_expr.split(":", 1)
                else:
                    var_name = var_expr
                    default = None

                var_key = var_name.strip().upper()
                # 优先从 _data 查找（环境变量），其次 _env_vars
                result = self._data.get(var_key) or self._env_vars.get(var_key)
                if result is None:
                    result = default or ""
                return str(result)

            # 替换 ${} 语法
            replaced = re.sub(r'\$\{([^}]+)\}', replace_var, data)
            self._data[prefix.upper()] = replaced
        else:
            self._data[prefix.upper()] = data

    @classmethod
    def get_instance(cls) -> "Config":
        """获取配置实例"""
        if cls._instance is None:
            raise RuntimeError("Config 未加载，请先调用 Config.load()")
        return cls._instance

    @classmethod
    def is_loaded(cls) -> bool:
        """检查是否已加载"""
        return cls._loaded

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（通用方法）

        Args:
            key: 配置键（不区分大小写，自动转大写）
            default: 默认值

        Returns:
            配置值或默认值
        """
        return self._data.get(key.upper(), default)

    def get_github_repos(self) -> list[str]:
        """获取 GitHub 仓库列表"""
        repos = self.get("REPOS", "")
        if not repos:
            return []
        return [r.strip() for r in repos.split(",") if r.strip()]

    def get_agent_type(self) -> str:
        """获取 Agent 类型"""
        return self.get("AGENT_TYPE", "mock")

    def get_deerflow_base_url(self) -> str:
        """获取 DeerFlow API 地址"""
        return self.get("DEERFLOW_BASE_URL", "http://localhost:2026")

    def get_poll_interval(self) -> int:
        """获取轮询间隔（秒）"""
        return int(self.get("POLL_INTERVAL", "60"))

    def get_issue_label(self) -> str:
        """获取监听标签"""
        return self.get("ISSUE_LABEL", "swallow")

    def get_base_branch(self) -> str:
        """获取基础分支"""
        return self.get("BASE_BRANCH", "main")

    def get_max_workers(self) -> int:
        """获取最大 Worker 数量"""
        return int(self.get("MAX_WORKERS", "5"))

    def get_work_dir(self) -> Path:
        """获取工作目录"""
        return Path(self.get("WORK_DIR", Path.home() / ".swallowloop"))

    def get_log_dir(self) -> Path:
        """获取日志目录"""
        return Path(self.get("LOG_DIR", self.get_work_dir() / "logs"))

    def get_llm_config(self) -> "dict":
        """获取 LLM 配置字典"""
        return {
            "provider": self.get("LLM_PROVIDER", "minimax"),
            "api_key": self.get("LLM_API_KEY") or self.get("OPENAI_API_KEY"),
            "base_url": self.get("LLM_BASE_URL") or self.get("OPENAI_API_BASE_URL", "https://api.minimaxi.com/v1"),
            "model_name": self.get("LLM_MODEL_NAME") or self.get("LLM_MODEL", "").split("/", 1)[-1] if "/" in self.get("LLM_MODEL", "") else self.get("LLM_MODEL", "m2.7"),
        }

    @property
    def workspaces_dir(self) -> Path:
        """工作空间目录"""
        return self.get_work_dir() / "workspaces"

    @property
    def codebase_dir(self) -> Path:
        """代码库缓存目录"""
        return self.get_work_dir() / "codebase"

    @property
    def data_dir(self) -> Path:
        """数据目录"""
        return self.get_work_dir()

    @property
    def logs_dir(self) -> Path:
        """日志目录"""
        return self.get_log_dir()
