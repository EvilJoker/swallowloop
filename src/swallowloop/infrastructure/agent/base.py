"""Agent 抽象基类"""

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.model import Task
    from ..codebase import CodebaseManager


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    message: str
    files_changed: list[str] = field(default_factory=list)
    output: str = ""


class Agent(ABC):
    """
    代码生成代理接口
    
    定义执行任务生成代码的抽象操作
    """
    
    @abstractmethod
    def execute(
        self,
        task: "Task",
        workspace_path: Path,
    ) -> ExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务对象
            workspace_path: 工作空间路径
            
        Returns:
            ExecutionResult 执行结果
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """代理名称"""
        pass
    
    @staticmethod
    @abstractmethod
    def check_available() -> tuple[bool, str]:
        """检查代理是否可用"""
        pass
    
    # ==================== 公共 Git 操作 ====================
    
    @staticmethod
    def _run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
        """执行 git 命令"""
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
    
    @classmethod
    def _prepare_repo(
        cls,
        task: "Task",
        workspace_path: Path,
        codebase_manager: "CodebaseManager | None" = None,
        github_token: str | None = None,
    ) -> ExecutionResult:
        """准备仓库
        
        如果提供了 codebase_manager 和 github_token，使用缓存机制：
        1. 检查 codebase 缓存是否存在
        2. 不存在则克隆，存在则更新
        3. 从缓存复制到工作空间
        
        否则使用传统方式直接克隆。
        """
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        git_dir = workspace_path / ".git"
        if git_dir.exists():
            # 工作空间已有仓库，更新即可
            try:
                cls._run_git(["fetch", "origin"], workspace_path)
                cls._run_git(["checkout", "main"], workspace_path)
                cls._run_git(["pull", "origin", "main"], workspace_path)
            except subprocess.CalledProcessError as e:
                return ExecutionResult(False, f"更新仓库失败: {e.stderr or str(e)}")
            return ExecutionResult(True, "仓库准备完成")
        
        # 使用 CodebaseManager 缓存机制
        if codebase_manager and github_token:
            try:
                # 1. 准备缓存仓库
                codebase_manager.prepare_codebase(github_token)
                # 2. 复制到工作空间
                repo_path = codebase_manager.copy_to_workspace(workspace_path)
                # 3. 将仓库内容移动到工作空间根目录
                import shutil
                for item in repo_path.iterdir():
                    if item.name != ".git":
                        shutil.move(str(item), str(workspace_path / item.name))
                # 移动 .git 目录
                git_cache = repo_path / ".git"
                git_target = workspace_path / ".git"
                if git_cache.exists():
                    shutil.move(str(git_cache), str(git_target))
                # 删除空的临时目录
                repo_path.rmdir()
            except Exception as e:
                return ExecutionResult(False, f"缓存复制失败: {str(e)}")
            return ExecutionResult(True, "仓库准备完成（使用缓存）")
        
        # 传统方式：直接克隆
        try:
            cls._run_git(["clone", task.repo_url, "."], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"克隆仓库失败: {e.stderr or str(e)}")
        return ExecutionResult(True, "仓库准备完成")
    
    @classmethod
    def _setup_branch(cls, task: "Task", workspace_path: Path) -> ExecutionResult:
        """设置分支"""
        try:
            result = cls._run_git(["checkout", task.branch_name], workspace_path, check=False)
            if result.returncode != 0:
                cls._run_git(["checkout", "-b", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"分支操作失败: {e.stderr or str(e)}")
        return ExecutionResult(True, "分支设置完成")
    
    @classmethod
    def _get_changed_files(cls, repo_path: Path) -> list[str]:
        """获取所有变化的文件（包括未跟踪的）"""
        try:
            result = cls._run_git(["status", "--porcelain"], repo_path)
            files = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line[3:].split(" -> ")
                    if len(parts) == 2:
                        files.append(parts[1].strip())
                    else:
                        files.append(line[3:].strip())
            return [f for f in files if f]
        except subprocess.CalledProcessError:
            return []
    
    @classmethod
    def _commit_and_push(cls, task: "Task", workspace_path: Path, files_changed: list[str]) -> ExecutionResult:
        """提交并推送"""
        try:
            cls._run_git(["add", "-A"], workspace_path)
            cls._run_git(["commit", "-m", f"Issue#{task.issue_number}: {task.title}"], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"提交失败: {e.stderr or str(e)}", files_changed)
        
        try:
            cls._run_git(["push", "-u", "origin", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"推送失败: {e.stderr or str(e)}", files_changed)
        
        return ExecutionResult(True, "任务完成，等待 PR 创建", files_changed)
    
    @classmethod
    def _prepare_revision(cls, task: "Task", workspace_path: Path) -> ExecutionResult:
        """准备修改任务（切换分支并拉取最新）
        
        支持浅克隆仓库：fetch 时指定深度获取远程分支
        """
        try:
            # 先尝试直接 fetch（完整仓库）
            result = cls._run_git(["fetch", "origin"], workspace_path, check=False)
            if result.returncode != 0:
                # 可能是浅克隆，尝试 fetch 指定分支
                result = cls._run_git(
                    ["fetch", "--depth", "1", "origin", task.branch_name],
                    workspace_path,
                    check=False
                )
            
            cls._run_git(["checkout", task.branch_name], workspace_path)
            cls._run_git(["reset", "--hard", f"origin/{task.branch_name}"], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"切换分支失败: {e.stderr or str(e)}")
        return ExecutionResult(True, "分支切换完成")
    
    @classmethod
    def _amend_and_push(cls, task: "Task", workspace_path: Path, files_changed: list[str]) -> ExecutionResult:
        """Amend 提交并强制推送"""
        try:
            cls._run_git(["add", "-A"], workspace_path)
            cls._run_git(["commit", "--amend", "--no-edit"], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"Amend 提交失败: {e.stderr or str(e)}", files_changed)
        
        try:
            cls._run_git(["push", "-f", "origin", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"强制推送失败: {e.stderr or str(e)}", files_changed)
        
        return ExecutionResult(True, "修改完成", files_changed)
    
    @staticmethod
    def _build_prompt(task: "Task") -> str:
        """构建任务提示"""
        from ...domain.model import TaskType
        
        if task.task_type == TaskType.REVISION:
            latest_comment = task.latest_comment
            feedback = latest_comment.body if latest_comment else task.description
            return f"""根据审核反馈修改代码:

**Issue:** {task.title}

**反馈内容:**
{feedback}

请根据反馈修改相关代码，确保满足审核要求。修改完成后，请确保代码可以正常运行。"""
        else:
            return f"""请解决以下 GitHub Issue:

**标题:** {task.title}

**描述:**
{task.description}

请:
1. 分析问题
2. 修改相关代码
3. 确保修改符合项目现有风格
4. 确保代码可以正常运行

完成后请总结你做的修改。"""