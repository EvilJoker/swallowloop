"""Settings API 路由"""

import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# .env 文件路径 (settings.py -> api -> web -> interfaces -> swallowloop -> src -> project_root)
ENV_FILE = Path(__file__).parent.parent.parent.parent.parent.parent / ".env"


def mask_secret(value: str) -> str:
    """掩码敏感信息，只显示前4位和后4位"""
    if not value or len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def unmask_secret(value: str, original: str) -> str:
    """如果值是掩码，保持原值不变"""
    if value == "****" or value == mask_secret(original):
        return original
    return value


class SettingsResponse(BaseModel):
    """设置响应"""
    github_repos: list[str]  # 多仓库列表
    llm_api_key: str  # 掩码后的 key
    llm_base_url: str
    llm_model: str
    agent_type: str
    poll_interval: int
    issue_label: str
    base_branch: str
    max_workers: int
    # 环境变量覆盖标记
    env_overrides: dict[str, bool]  # 哪些配置被环境变量覆盖


class SettingsUpdate(BaseModel):
    """设置更新请求"""
    github_repos: Optional[list[str]] = None
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    agent_type: Optional[str] = None
    poll_interval: Optional[int] = None
    issue_label: Optional[str] = None
    base_branch: Optional[str] = None
    max_workers: Optional[int] = None


def _load_env_file() -> dict[str, str]:
    """加载 .env 文件内容"""
    if not ENV_FILE.exists():
        return {}
    result = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _save_env_file(settings: dict[str, str]) -> None:
    """保存设置到 .env 文件"""
    # 读取现有内容（保留注释）
    existing_lines = []
    if ENV_FILE.exists():
        existing_lines = ENV_FILE.read_text().splitlines()

    # 更新或添加设置
    new_settings = set(settings.keys())
    updated_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            updated_lines.append(line)
            continue
        if "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in settings:
                updated_lines.append(f"{key}={settings[key]}")
                new_settings.discard(key)
            else:
                updated_lines.append(line)

    # 添加新设置
    for key in new_settings:
        updated_lines.append(f"{key}={settings[key]}")

    ENV_FILE.write_text("\n".join(updated_lines) + "\n")


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """获取当前设置"""
    env_vars = _load_env_file()

    # 获取环境变量（优先级更高），fallback 到 .env 文件
    repos_str = os.getenv("REPOS", env_vars.get("REPOS", ""))
    github_repos = [r.strip() for r in repos_str.split(",") if r.strip()] if repos_str else []
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "") or env_vars.get("OPENAI_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_API_BASE_URL", "") or env_vars.get("OPENAI_API_BASE_URL", "")
    llm_model = os.getenv("LLM_MODEL", env_vars.get("LLM_MODEL", ""))
    agent_type = os.getenv("AGENT_TYPE", env_vars.get("AGENT_TYPE", "mock"))
    poll_interval = int(os.getenv("POLL_INTERVAL", env_vars.get("POLL_INTERVAL", "60")))
    issue_label = os.getenv("ISSUE_LABEL", env_vars.get("ISSUE_LABEL", "swallow"))
    base_branch = os.getenv("BASE_BRANCH", env_vars.get("BASE_BRANCH", "main"))
    max_workers = int(os.getenv("MAX_WORKERS", env_vars.get("MAX_WORKERS", "5")))

    # 检查哪些被环境变量覆盖
    env_overrides = {
        "github_repos": bool(os.getenv("REPOS")),
        "llm_api_key": bool(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")),
        "llm_base_url": bool(os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_API_BASE_URL")),
        "llm_model": bool(os.getenv("LLM_MODEL")),
        "agent_type": bool(os.getenv("AGENT_TYPE")),
        "poll_interval": bool(os.getenv("POLL_INTERVAL")),
        "issue_label": bool(os.getenv("ISSUE_LABEL")),
        "base_branch": bool(os.getenv("BASE_BRANCH")),
        "max_workers": bool(os.getenv("MAX_WORKERS")),
    }

    return SettingsResponse(
        github_repos=github_repos,
        llm_api_key=mask_secret(llm_api_key),
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        agent_type=agent_type,
        poll_interval=poll_interval,
        issue_label=issue_label,
        base_branch=base_branch,
        max_workers=max_workers,
        env_overrides=env_overrides,
    )


@router.put("/settings")
async def update_settings(settings: SettingsUpdate):
    """更新设置（保存到 .env 文件）"""
    if not ENV_FILE.exists():
        raise HTTPException(status_code=400, detail=".env 文件不存在")

    # 加载当前 .env 设置
    current = _load_env_file()

    # 读取原始 token/key（用于比较）
    original_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or current.get("OPENAI_API_KEY", "")

    # 更新设置（只更新提供的字段）
    update_dict = settings.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        if value is not None:
            if key == "github_repos":
                current["REPOS"] = ",".join(value)
            elif key == "llm_api_key":
                value = unmask_secret(value, original_api_key)
                # 兼容旧变量名
                if "OPENAI_API_KEY" in current:
                    current["OPENAI_API_KEY"] = value
                else:
                    current["LLM_API_KEY"] = value
            else:
                current[key.upper()] = str(value)

    # 保存到文件
    _save_env_file(current)

    return {"status": "ok", "message": "设置已保存，重启后生效"}
