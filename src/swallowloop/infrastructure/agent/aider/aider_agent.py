"""Aider Agent 实现"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..base import Agent, ExecutionResult
from ....domain.model import Task, TaskType


@dataclass
class AiderConfig:
    """Aider 配置"""
    model: str = "claude-sonnet-4-20250514"
    timeout: int = 600
    llm_provider_config: dict[str, Any] | None = None


class AiderAgent(Agent):
    """
    Aider Agent 实现
    
    使用 Aider CLI 进行代码开发
    """
    
    def __init__(self, config: AiderConfig):
        self._config = config
    
    @property
    def name(self) -> str:
        return "aider"
    
    def execute(
        self,
        task: Task,
        workspace_path: Path,
    ) -> ExecutionResult:
        """执行任务"""
        if task.task_type == TaskType.NEW_TASK:
            return self._execute_new_task(task, workspace_path)
        else:
            return self._execute_revision(task, workspace_path)
    
    def _execute_new_task(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """
        执行新任务
        
        流程：
        1. 检查/克隆仓库
        2. 创建分支
        3. 运行 Aider
        4. 提交并推送
        """
        # 构建 clone URL（使用 token 认证）
        clone_url = task.repo_url
        
        # 1. 检查仓库是否已存在
        git_dir = workspace_path / ".git"
        if git_dir.exists():
            # 仓库已存在，拉取最新代码
            try:
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "checkout", "main"],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "pull", "origin", "main"],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return ExecutionResult(
                    success=False,
                    message=f"更新仓库失败: {e.stderr.decode() if e.stderr else str(e)}",
                )
        else:
            # 仓库不存在，克隆
            try:
                subprocess.run(
                    ["git", "clone", clone_url, "."],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return ExecutionResult(
                    success=False,
                    message=f"克隆仓库失败: {e.stderr.decode() if e.stderr else str(e)}",
                )
        
        # 2. 创建或切换分支
        try:
            result = subprocess.run(
                ["git", "checkout", task.branch_name],
                cwd=workspace_path,
                capture_output=True
            )
            if result.returncode != 0:
                # 分支不存在，创建新分支
                subprocess.run(
                    ["git", "checkout", "-b", task.branch_name],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
        except subprocess.CalledProcessError as e:
            return ExecutionResult(
                success=False,
                message=f"分支操作失败: {e.stderr.decode() if e.stderr else str(e)}",
            )
        
        # 3. 运行 Aider
        task_prompt = self._build_prompt(task)
        result = self._run_aider(workspace_path, task_prompt)
        
        if not result.success:
            return result
        
        # 4. 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(
                success=False,
                message="Aider 未修改任何文件",
            )
        
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"Issue#{task.issue_number}: {task.title}"],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return ExecutionResult(
                success=False,
                message=f"提交失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=files_changed,
            )
        
        # 5. 推送
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", task.branch_name],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return ExecutionResult(
                success=False,
                message=f"推送失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=files_changed,
            )
        
        return ExecutionResult(
            success=True,
            message="任务完成，等待 PR 创建",
            files_changed=files_changed,
            output=result.output,
        )
    
    def _execute_revision(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """
        执行修改任务
        
        流程：
        1. 切换到现有分支
        2. 拉取最新代码
        3. 运行 Aider
        4. amend 提交
        5. 强制推送
        """
        # 1. 切换分支并拉取最新
        try:
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "checkout", task.branch_name],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "reset", "--hard", f"origin/{task.branch_name}"],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return ExecutionResult(
                success=False,
                message=f"切换分支失败: {e.stderr.decode() if e.stderr else str(e)}",
            )
        
        # 2. 运行 Aider
        task_prompt = self._build_prompt(task)
        result = self._run_aider(workspace_path, task_prompt)
        
        if not result.success:
            return result
        
        # 3. amend 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(
                success=True,
                message="无需修改",
            )
        
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "commit", "--amend", "--no-edit"],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return ExecutionResult(
                success=False,
                message=f"Amend 提交失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=files_changed,
            )
        
        # 4. 强制推送
        try:
            subprocess.run(
                ["git", "push", "-f", "origin", task.branch_name],
                cwd=workspace_path,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            return ExecutionResult(
                success=False,
                message=f"强制推送失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=files_changed,
            )
        
        return ExecutionResult(
            success=True,
            message="修改完成",
            files_changed=files_changed,
            output=result.output,
        )
    
    def _run_aider(self, repo_path: Path, prompt: str) -> ExecutionResult:
        """运行 Aider"""
        cmd = [
            "aider",
            f"--model", self._config.model,
            "--yes",
            "--no-auto-commits",
            "--no-dirty-commits",
            "--no-show-model-warnings",
            "--message", prompt,
        ]
        
        env = os.environ.copy()
        
        # 传递 LLM Provider 配置
        if self._config.llm_provider_config:
            env.update(self._config.llm_provider_config)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                env=env,
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
            return ExecutionResult(
                success=False,
                message=f"执行超时（{self._config.timeout}秒）",
            )
        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                message="Aider 未安装，请执行: pip install aider-chat",
            )
    
    def _get_changed_files(self, repo_path: Path) -> list[str]:
        """获取所有变化的文件（包括未跟踪的）"""
        try:
            # git status --porcelain 输出格式: XY filename
            # X = 索引状态, Y = 工作树状态
            # ?? = 未跟踪文件, A = 新增, M = 修改, D = 删除
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            files = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    # 格式: "XY filename" 或 "XY old -> new" (重命名)
                    parts = line[3:].split(" -> ")
                    if len(parts) == 2:
                        files.append(parts[1].strip())
                    else:
                        files.append(line[3:].strip())
            return [f for f in files if f]
        except subprocess.CalledProcessError:
            return []
    
    def _build_prompt(self, task: Task) -> str:
        """构建任务提示"""
        if task.task_type == TaskType.REVISION:
            latest_comment = task.latest_comment
            feedback = latest_comment.body if latest_comment else task.description
            return f"""根据审核反馈修改代码:

**Issue:** {task.title}

**反馈内容:**
{feedback}

请根据反馈修改相关代码，确保满足审核要求。
"""
        else:
            return f"""请解决以下 GitHub Issue:

**标题:** {task.title}

**描述:**
{task.description}

请:
1. 分析问题
2. 修改相关代码
3. 确保修改符合项目现有风格
"""
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        """检查 Aider 是否可用"""
        try:
            result = subprocess.run(
                ["aider", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, "aider 命令执行失败"
        except FileNotFoundError:
            return False, "aider 未安装，请执行: pip install aider-chat"
