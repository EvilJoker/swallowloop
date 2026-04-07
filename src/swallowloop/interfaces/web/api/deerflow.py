"""DeerFlow Status API 路由"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ....infrastructure.agent import AgentStatus
from ....infrastructure.instance_registry import get_instance
from ....infrastructure.constants import DEFAULT_DEERFLOW_BASE_URL

router = APIRouter()


class DeerFlowStatusResponse(BaseModel):
    """DeerFlow 状态响应"""
    # 服务状态
    status: str  # "online" | "offline"
    version: Optional[str] = None

    # AI 模型
    model_name: Optional[str] = None
    model_display_name: Optional[str] = None

    # LLM 用量（每5小时刷新）
    llm_used: int = 0
    llm_quota: int = 1500
    llm_next_refresh: Optional[str] = None  # ISO 格式时间

    # 连接信息
    base_url: str
    data_dir: str
    active_threads: int = 0


def _get_data_dir() -> str:
    """获取 DeerFlow 数据目录"""
    config = get_instance("config")
    data_dir = config.get("DEERFLOW_DATA_DIR") if config else None
    if data_dir:
        # 展开 ~ 和环境变量
        return str(Path(data_dir).expanduser().resolve())
    return str(Path.home() / ".deer-flow")


def _get_deerflow_base_url() -> str:
    """获取 DeerFlow 基础 URL"""
    config = get_instance("config")
    return config.get("DEERFLOW_BASE_URL", DEFAULT_DEERFLOW_BASE_URL) if config else DEFAULT_DEERFLOW_BASE_URL


@router.get("/deerflow/status", response_model=DeerFlowStatusResponse)
async def get_deerflow_status():
    """获取 DeerFlow 状态信息（从 Agent 缓存返回，毫秒级响应）"""
    agent = get_instance("agent")
    status: AgentStatus = agent.get_status() if agent else AgentStatus()

    return DeerFlowStatusResponse(
        status=status.status,
        version=status.version,
        model_name=status.model_name,
        model_display_name=status.model_display_name,
        llm_used=status.llm_used,
        llm_quota=status.llm_quota,
        llm_next_refresh=status.llm_next_refresh,
        base_url=status.base_url or _get_deerflow_base_url(),
        data_dir=_get_data_dir(),
        active_threads=status.active_threads,
    )
