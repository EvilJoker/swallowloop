"""Worker - 独立执行任务的进程"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .models import Task, TaskType


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    message: str
    files_changed: list[str] = field(default_factory=list)
    output: str = ""
    pr_url: str | None = None
    pr_number: int | None = None


class Worker:
    """
    Worker - 独立执行任务
    
    职责：
    - 克隆仓库（首次任务）或切换分支（修改任务）
    - 使用 Aider 进行代码开发
    - 提交代码并创建/更新 PR
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.model = config.llm_model
        self.timeout = config.worker_timeout
    
    def execute(self, task: Task, workspace_path: Path) -> TaskResult:
        """
        执行任务
        
        Args:
            task: 任务对象
            workspace_path: 工作空间路径
            
        Returns:
            TaskResult 执行结果
        """
        if task.task_type == TaskType.NEW_TASK:
            return self._execute_new_task(task, workspace_path)
        else:
            return self._execute_revision(task, workspace_path)
    
    def _execute_new_task(self, task: Task, workspace_path: Path) -> TaskResult:
        """
        执行新任务
        
        流程：
        1. 检查/克隆仓库
        2. 创建分支
        3. 运行 Aider
        4. 提交并推送
        5. 创建 PR
        """
        clone_url = f"https://{self.config.github_token}@github.com/{self.config.github_repo}.git"
        
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
                    ["git", "checkout", self.config.base_branch],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "pull", "origin", self.config.base_branch],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return TaskResult(
                    success=False,
                    message=f"更新仓库失败: {e.stderr.decode() if e.stderr else str(e)}",
                    files_changed=[],
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
                return TaskResult(
                    success=False,
                    message=f"克隆仓库失败: {e.stderr.decode() if e.stderr else str(e)}",
                    files_changed=[],
                )
        
        # 2. 创建或切换分支
        try:
            # 先尝试切换到现有分支
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
            return TaskResult(
                success=False,
                message=f"分支操作失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=[],
            )
        
        # 3. 运行 Aider
        task_prompt = self._build_prompt(task)
        result = self._run_aider(workspace_path, task_prompt)
        
        if not result.success:
            return result
        
        # 4. 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return TaskResult(
                success=False,
                message="Aider 未修改任何文件",
                files_changed=[],
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
            return TaskResult(
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
            return TaskResult(
                success=False,
                message=f"推送失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=files_changed,
            )
        
        # 6. 创建 PR（通过 GitHub API，这里先返回基本信息）
        return TaskResult(
            success=True,
            message="任务完成，等待 PR 创建",
            files_changed=files_changed,
            output=result.output,
        )
    
    def _execute_revision(self, task: Task, workspace_path: Path) -> TaskResult:
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
            return TaskResult(
                success=False,
                message=f"切换分支失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=[],
            )
        
        # 2. 运行 Aider
        task_prompt = self._build_prompt(task)
        result = self._run_aider(workspace_path, task_prompt)
        
        if not result.success:
            return result
        
        # 3. amend 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return TaskResult(
                success=True,
                message="无需修改",
                files_changed=[],
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
            return TaskResult(
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
            return TaskResult(
                success=False,
                message=f"强制推送失败: {e.stderr.decode() if e.stderr else str(e)}",
                files_changed=files_changed,
            )
        
        return TaskResult(
            success=True,
            message="修改完成",
            files_changed=files_changed,
            output=result.output,
        )
    
    def _run_aider(self, repo_path: Path, prompt: str) -> TaskResult:
        """运行 Aider"""
        cmd = [
            "aider",
            f"--model", self.model,
            "--yes",
            "--no-auto-commits",
            "--no-dirty-commits",
            "--no-show-model-warnings",
            "--message", prompt,
        ]
        
        env = os.environ.copy()
        
        # 传递 OpenAI API 配置给 aider
        # aider 使用 AIDER_OPENAI_API_BASE 而不是 OPENAI_API_BASE_URL
        if self.config.openai_api_key:
            env["OPENAI_API_KEY"] = self.config.openai_api_key
        if self.config.openai_api_base_url:
            env["AIDER_OPENAI_API_BASE"] = self.config.openai_api_base_url
        
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                env=env,
                timeout=self.timeout,
            )
            
            output = result.stdout + "\n" + result.stderr
            success = result.returncode == 0
            
            return TaskResult(
                success=success,
                message="Aider 完成" if success else "Aider 执行失败",
                files_changed=[],
                output=output,
            )
            
        except subprocess.TimeoutExpired:
            return TaskResult(
                success=False,
                message=f"执行超时（{self.timeout}秒）",
                files_changed=[],
            )
        except FileNotFoundError:
            return TaskResult(
                success=False,
                message="Aider 未安装，请执行: pip install aider-chat",
                files_changed=[],
            )
    
    def _get_changed_files(self, repo_path: Path) -> list[str]:
        """获取已修改但未提交的文件"""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            
            result2 = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            staged = [f.strip() for f in result2.stdout.strip().split("\n") if f.strip()]
            
            return list(set(files + staged))
        except subprocess.CalledProcessError:
            return []
    
    def _build_prompt(self, task: Task) -> str:
        """构建任务提示"""
        if task.task_type == TaskType.REVISION:
            return f"""根据审核反馈修改代码:

**Issue:** {task.title}

**反馈内容:**
{task.description}

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
