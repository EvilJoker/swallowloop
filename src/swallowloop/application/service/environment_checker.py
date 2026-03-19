"""环境检查器 - Worker 启动前的环境检查"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class EnvironmentCheckResult:
    """环境检查结果"""
    ok: bool
    message: str
    details: dict


# Agent 可用性检查函数类型
AgentCheckFunc = Callable[[], tuple[bool, str]]


class EnvironmentChecker:
    """
    Worker 启动前的环境检查器

    检查项：
    1. 工作空间是否存在
    2. 依赖是否完整
    3. Git 配置是否正确
    4. Agent 是否可用
    """

    def __init__(self, workspace_path: Path, agent_check: AgentCheckFunc | None = None):
        self._workspace = workspace_path
        self._agent_check = agent_check

    def check(self) -> EnvironmentCheckResult:
        """执行所有环境检查"""
        checks = [
            ("workspace", self._check_workspace),
            ("dependencies", self._check_dependencies),
            ("git_config", self._check_git_config),
            ("agent", self._check_agent),
        ]

        results = {}
        all_ok = True

        for name, check_func in checks:
            ok, msg = check_func()
            results[name] = {"ok": ok, "message": msg}
            if not ok:
                all_ok = False

        if all_ok:
            return EnvironmentCheckResult(
                ok=True,
                message="环境检查通过",
                details=results
            )
        else:
            failed = [name for name, r in results.items() if not r["ok"]]
            return EnvironmentCheckResult(
                ok=False,
                message=f"环境检查失败: {', '.join(failed)}",
                details=results
            )

    def _check_workspace(self) -> tuple[bool, str]:
        """检查工作空间"""
        if not self._workspace.exists():
            return False, f"工作空间不存在: {self._workspace}"

        if not self._workspace.is_dir():
            return False, f"工作空间不是目录: {self._workspace}"

        # 检查是否有读写权限
        if not os.access(self._workspace, os.R_OK | os.W_OK):
            return False, f"工作空间没有读写权限: {self._workspace}"

        return True, f"工作空间正常: {self._workspace}"

    def _check_dependencies(self) -> tuple[bool, str]:
        """检查依赖是否完整"""
        # 检查 .venv 是否存在
        venv_path = self._workspace / ".venv"
        if not venv_path.exists():
            return False, "虚拟环境不存在，请先运行 uv sync"

        # 检查关键依赖
        uv_lock = self._workspace / "uv.lock"
        if not uv_lock.exists():
            return False, "uv.lock 不存在，依赖可能未安装"

        # 检查 Python 解释器
        python_path = venv_path / "bin" / "python"
        if not python_path.exists():
            return False, "Python 解释器不存在"

        return True, "依赖检查通过"

    def _check_git_config(self) -> tuple[bool, str]:
        """检查 Git 配置"""
        git_dir = self._workspace / ".git"
        if not git_dir.exists():
            return False, ".git 目录不存在"

        # 检查 origin 是否设置
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self._workspace,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, "Git origin 未设置"

            origin_url = result.stdout.strip()
            if not origin_url:
                return False, "Git origin URL 为空"

            return True, f"Git origin: {origin_url[:50]}..."

        except subprocess.TimeoutExpired:
            return False, "Git 命令超时"
        except Exception as e:
            return False, f"Git 配置检查失败: {e}"

    def _check_agent(self) -> tuple[bool, str]:
        """检查 Agent 可用性"""
        if self._agent_check is None:
            return True, "未配置 Agent 检查"
        return self._agent_check()
