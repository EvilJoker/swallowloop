"""环境准备 - Clone 代码库任务"""

import os
import shutil
import subprocess
from ..task import Task, TaskResult


class EnvironmentCloneRepoTask(Task):
    """环境准备 - Clone 代码库任务"""

    def __init__(self):
        super().__init__(
            name="Clone 代码库",
            handler=self._execute,
            description="克隆目标代码仓库到工作空间"
        )

    def _execute(self, context: dict) -> TaskResult:
        """执行 Clone 仓库"""
        workspace_path = context.get("workspace_path")
        repo_url = context.get("repo_url")
        repo_name = context.get("repo_name", "repo")

        if not workspace_path:
            return TaskResult(success=False, message="workspace_path 未指定")

        # 代码放到 workspace_path/{repo_name}/ 目录下
        repo_path = os.path.join(workspace_path, repo_name)

        # 如果没有 repo_url，从配置获取默认仓库
        if not repo_url:
            # 尝试从环境变量或配置获取默认仓库
            default_repo = os.getenv("GITHUB_REPO", "EvilJoker/swallowloop")
            # 构造 GitHub HTTPS URL
            github_token = os.getenv("GITHUB_TOKEN", "")
            if github_token:
                repo_url = f"https://{github_token}@github.com/{default_repo}.git"
            else:
                repo_url = f"https://github.com/{default_repo}.git"

        # 检查是否已经是 git 仓库
        git_dir = os.path.join(repo_path, ".git")
        if os.path.isdir(git_dir):
            return TaskResult(success=True, message=f"已是 git 仓库，跳过克隆: {repo_path}")

        # 如果目录存在且不为空，先清理
        if os.path.exists(repo_path) and os.listdir(repo_path):
            try:
                shutil.rmtree(repo_path)
            except Exception as e:
                return TaskResult(success=False, message=f"清理目录失败: {str(e)}")

        try:
            # 执行 git clone 到 repo_path 子目录
            result = subprocess.run(
                ["git", "clone", repo_url, repo_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                # 更新 context 中的 workspace_path 为实际代码路径
                context["repo_path"] = repo_path
                return TaskResult(success=True, message=f"仓库已克隆到: {repo_path}")
            else:
                return TaskResult(success=False, message=f"克隆失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            return TaskResult(success=False, message="克隆超时")
        except Exception as e:
            return TaskResult(success=False, message=f"克隆异常: {str(e)}")
