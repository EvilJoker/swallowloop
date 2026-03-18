"""配置管理"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    """SwallowLoop 配置"""
    
    # GitHub 配置
    github_token: str
    github_repo: str  # owner/repo 格式
    
    # LLM 配置
    llm_model: str = "gpt-4o"
    
    # Agent 配置
    agent_type: str = "iflow"  # iflow, aider
    agent_timeout: int = 600
    
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
        
        work_dir = os.getenv("WORK_DIR")
        if work_dir:
            work_dir = Path(work_dir)
        
        log_dir = os.getenv("LOG_DIR")
        if log_dir:
            log_dir = Path(log_dir)
        
        return cls(
            github_token=github_token,
            github_repo=github_repo,
            llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
            agent_type=os.getenv("AGENT_TYPE", "iflow"),
            agent_timeout=int(os.getenv("AGENT_TIMEOUT", "600")),
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