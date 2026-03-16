"""配置管理"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """SwallowLoop 配置"""
    
    # GitHub 配置
    github_token: str
    github_repo: str  # owner/repo 格式
    
    # OpenAI API 配置 (用于 aider)
    openai_api_key: str | None = None
    openai_api_base_url: str | None = None
    
    # 工作目录
    work_dir: Path | None = None  # 工作目录，默认 ~/.swallowloop/workspaces
    
    # 任务监听配置
    poll_interval: int = 60  # 轮询间隔(秒)
    issue_label: str = "swallow"  # 监听的Issue标签
    base_branch: str = "main"  # 默认基础分支
    
    # Worker Agent 配置
    agent_type: str = "iflow"  # iflow 或 aider
    llm_model: str = "claude-sonnet-4-20250514"  # Aider 使用的模型
    worker_timeout: int = 600  # Worker 超时(秒)
    auto_test: bool = False  # 是否自动运行测试
    
    @classmethod
    def from_env(cls, dotenv_path: str | Path | None = None) -> "Config":
        """
        从环境变量加载配置
        
        Args:
            dotenv_path: .env 文件路径，默认自动查找
        """
        # 加载 .env 文件
        load_dotenv(dotenv_path)
        
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError(
                "GITHUB_TOKEN 环境变量未设置\n"
                "请创建 .env 文件或设置环境变量:\n"
                "  cp .env.example .env\n"
                "  编辑 .env 填入配置"
            )
        
        github_repo = os.getenv("GITHUB_REPO")
        if not github_repo:
            raise ValueError("GITHUB_REPO 环境变量未设置 (格式: owner/repo)")
        
        work_dir = os.getenv("WORK_DIR")
        if work_dir:
            work_dir = Path(work_dir)
        
        return cls(
            github_token=github_token,
            github_repo=github_repo,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base_url=os.getenv("OPENAI_API_BASE_URL"),
            work_dir=work_dir,
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
            issue_label=os.getenv("ISSUE_LABEL", "swallow"),
            base_branch=os.getenv("BASE_BRANCH", "main"),
            agent_type=os.getenv("AGENT_TYPE", "iflow"),
            llm_model=os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"),
            worker_timeout=int(os.getenv("WORKER_TIMEOUT", "600")),
            auto_test=os.getenv("AUTO_TEST", "false").lower() == "true",
        )
