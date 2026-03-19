"""配置管理"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from ..llm import LLMConfig


@dataclass
class Settings:
    """SwallowLoop 配置"""
    
    # GitHub 配置
    github_token: str
    github_repo: str  # 单个仓库 owner/repo 格式（兼容旧配置）
    github_repos: list[str] = field(default_factory=list)  # 多仓库列表
    
    # Agent 配置
    agent_timeout: int = 1200  # Agent 超时时间（秒），默认 20 分钟
    
    # Worker 并发配置
    max_workers: int = 5  # 最大并发 Worker 数量
    
    # 工作目录
    work_dir: Path | None = None
    
    # 任务监听配置
    poll_interval: int = 60
    issue_label: str = "swallow"
    base_branch: str = "main"
    
    # 日志配置
    log_level: str = "INFO"
    log_dir: Path | None = None
    
    # Web Dashboard 配置
    web_enabled: bool = True  # 是否启用 Web Dashboard
    web_port: int = 8080  # Web 服务端口
    web_host: str = "0.0.0.0"  # Web 服务监听地址
    
    # 自更新配置
    enable_self_update: bool = True  # 是否启用自更新
    self_update_interval: int = 300  # 检查更新的间隔（秒），默认5分钟
    
    # LLM 配置（独立管理，Agent 从这里获取配置）
    llm_config: "LLMConfig | None" = None
    
    @classmethod
    def from_env(cls, dotenv_path: str | Path | None = None) -> "Settings":
        """从环境变量加载配置"""
        load_dotenv(dotenv_path)
        
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN 环境变量未设置\n"
                "请创建 .env 文件或设置环境变量"
            )
        
        github_repo = os.getenv("GITHUB_REPO")
        if not github_repo:
            raise ValueError("GITHUB_REPO 环境变量未设置 (格式: owner/repo)")
        
        # 支持多仓库配置（逗号分隔）
        github_repos_str = os.getenv("GITHUB_REPOS", "")
        if github_repos_str:
            # 解析逗号分隔的仓库列表
            github_repos = [r.strip() for r in github_repos_str.split(",") if r.strip()]
        else:
            # 兼容旧配置：单仓库
            github_repos = [github_repo] if github_repo else []
        
        work_dir = os.getenv("WORK_DIR")
        if work_dir:
            work_dir = Path(work_dir)
        
        log_dir = os.getenv("LOG_DIR")
        if log_dir:
            log_dir = Path(log_dir)
        
        # 加载 LLM 配置
        llm_config = cls._load_llm_config()
        
        return cls(
            github_token=github_token,
            github_repo=github_repo,
            github_repos=github_repos,
            agent_timeout=int(os.getenv("AGENT_TIMEOUT", "1200")),
            max_workers=int(os.getenv("MAX_WORKERS", "5")),
            work_dir=work_dir,
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
            issue_label=os.getenv("ISSUE_LABEL", "swallow"),
            base_branch=os.getenv("BASE_BRANCH", "main"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=log_dir,
            web_enabled=os.getenv("WEB_ENABLED", "true").lower() == "true",
            web_port=int(os.getenv("WEB_PORT", "8080")),
            web_host=os.getenv("WEB_HOST", "0.0.0.0"),
            enable_self_update=os.getenv("ENABLE_SELF_UPDATE", "true").lower() == "true",
            self_update_interval=int(os.getenv("SELF_UPDATE_INTERVAL", "300")),
            llm_config=llm_config,
        )
    
    @staticmethod
    def _load_llm_config() -> "LLMConfig | None":
        """从环境变量加载 LLM 配置
        
        支持两种方式：
        1. 使用 LLM_* 前缀的环境变量
        2. 兼容旧的 OPENAI_API_KEY / OPENAI_API_BASE_URL / LLM_MODEL
        """
        from ..llm import LLMConfig, LLMProvider
        
        # 方式1: 使用 LLM_* 环境变量
        llm_provider = os.getenv("LLM_PROVIDER", "").lower()
        llm_api_key = os.getenv("LLM_API_KEY")
        llm_base_url = os.getenv("LLM_BASE_URL")
        llm_model_name = os.getenv("LLM_MODEL_NAME")
        
        # 方式2: 兼容旧的环境变量（OPENAI_API_KEY 可能是 Minimax 的 key）
        if not llm_api_key:
            llm_api_key = os.getenv("OPENAI_API_KEY")
        if not llm_base_url:
            llm_base_url = os.getenv("OPENAI_API_BASE_URL")
        if not llm_model_name:
            # 从 LLM_MODEL 解析，如 "openai/MiniMax-M2.5-highspeed"
            llm_model = os.getenv("LLM_MODEL", "")
            if "/" in llm_model:
                llm_model_name = llm_model.split("/", 1)[1]
            else:
                llm_model_name = llm_model if llm_model else None
        
        # 如果没有配置 API Key，使用默认配置
        if not llm_api_key:
            return None
        
        # 推断提供商
        if not llm_provider:
            if llm_base_url and "minimax" in llm_base_url.lower():
                llm_provider = "minimax"
            elif llm_base_url and "openai" in llm_base_url.lower():
                llm_provider = "openai"
            else:
                llm_provider = "custom"
        
        try:
            provider = LLMProvider(llm_provider)
        except ValueError:
            provider = LLMProvider.CUSTOM
        
        return LLMConfig(
            provider=provider,
            model_name=llm_model_name or "",
            api_key=llm_api_key,
            base_url=llm_base_url,
        )
    
    @property
    def workspaces_dir(self) -> Path:
        """工作空间目录"""
        return (self.work_dir or Path.home() / ".swallowloop") / "workspaces"
    
    @property
    def codebase_dir(self) -> Path:
        """代码库缓存目录"""
        return (self.work_dir or Path.home() / ".swallowloop") / "codebase"
    
    @property
    def data_dir(self) -> Path:
        """数据目录"""
        return self.work_dir or Path.home() / ".swallowloop"
    
    @property
    def logs_dir(self) -> Path:
        """日志目录"""
        return self.log_dir or (self.work_dir or Path.home() / ".swallowloop") / "logs"
    
    def get_llm_config(self) -> "LLMConfig":
        """获取 LLM 配置，如果没有配置则返回默认配置"""
        if self.llm_config is None:
            from ..llm import LLMConfig
            return LLMConfig.default()
        return self.llm_config
