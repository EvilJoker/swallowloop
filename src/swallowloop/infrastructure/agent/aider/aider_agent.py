"""Aider Agent 实现"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..base import Agent, ExecutionResult
from ....domain.model import Task, TaskType


@dataclass
class AiderConfig:
    """Aider 配置"""
    model: str = "claude-sonnet-4-20250514"
    timeout: int = 600


class AiderAgent(Agent):
    """Aider Agent 实现 - 使用 Aider CLI 进行代码开发"""
    
    def __init__(self, config: AiderConfig):
        self._config = config
    
    @property
    def name(self) -> str:
        return "aider"
    
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        if task.task_type == TaskType.NEW_TASK:
            return self._execute_new_task(task, workspace_path)
        else:
            return self._execute_revision(task, workspace_path)
    
    def _execute_new_task(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 1. 准备仓库
        result = self._prepare_repo(task, workspace_path)
        if not result.success:
            return result
        
        # 2. 设置分支
        result = self._setup_branch(task, workspace_path)
        if not result.success:
            return result
        
        # 3. 运行 Aider
        result = self._run_aider(workspace_path, self._build_prompt(task))
        if not result.success:
            return result
        
        # 4. 提交推送
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(False, "Aider 未修改任何文件")
        
        return self._commit_and_push(task, workspace_path, files_changed)
    
    def _execute_revision(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 1. 切换分支
        result = self._prepare_revision(task, workspace_path)
        if not result.success:
            return result
        
        # 2. 运行 Aider
        result = self._run_aider(workspace_path, self._build_prompt(task))
        if not result.success:
            return result
        
        # 3. Amend 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(True, "无需修改")
        
        return self._amend_and_push(task, workspace_path, files_changed)
    
    def _run_aider(self, repo_path: Path, prompt: str) -> ExecutionResult:
        """运行 Aider"""
        cmd = [
            "aider",
            "--model", self._config.model,
            "--yes",
            "--no-auto-commits",
            "--no-dirty-commits",
            "--no-show-model-warnings",
            "--message", prompt,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self._config.timeout,
            )
            
            output = result.stdout + "\n" + result.stderr
            success = result.returncode == 0
            
            return ExecutionResult(
                success=success,
                message="Aider 完成" if success else "Aider 执行失败",
                output=output,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(False, f"执行超时（{self._config.timeout}秒）")
        except FileNotFoundError:
            return ExecutionResult(False, "aider 未安装，请执行: pip install aider-chat")
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        try:
            result = subprocess.run(["aider", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "aider 命令执行失败"
        except FileNotFoundError:
            return False, "aider 未安装，请执行: pip install aider-chat"