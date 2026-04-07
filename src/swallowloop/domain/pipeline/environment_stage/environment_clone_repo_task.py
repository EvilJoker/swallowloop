"""环境准备 - Clone 代码库任务"""

import os
import shutil
import subprocess
import logging
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


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

        # 如果没有 repo_url，从环境变量获取
        if not repo_url:
            default_repo = os.getenv("REPOS", "")
            if not default_repo:
                return TaskResult(success=False, message="repo_url 未设置，且 REPOS 环境变量也未设置")
            default_repo = default_repo.split(",")[0].strip()
            repo_url = default_repo

        # 转换 shorthand 格式为完整 URL
        repo_url = self._normalize_repo_url(repo_url)

        logger.info(f"开始克隆仓库: {repo_url}")

        # 检查是否已经是 git 仓库
        git_dir = os.path.join(repo_path, ".git")
        if os.path.isdir(git_dir):
            context["repo_path"] = repo_path
            return TaskResult(success=True, message=f"已是 git 仓库，跳过克隆: {repo_path}", data={"repo_path": repo_path})

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
                # 更新 context 中的 repo_path
                context["repo_path"] = repo_path
                logger.info(f"仓库克隆成功: {repo_path}")
                return TaskResult(success=True, message=f"仓库已克隆到: {repo_path}", data={"repo_path": repo_path})
            else:
                error_msg = f"克隆失败: {result.stderr}"
                logger.error(error_msg)
                return TaskResult(success=False, message=error_msg)
        except subprocess.TimeoutExpired:
            return TaskResult(success=False, message="克隆超时（5分钟）")
        except Exception as e:
            error_msg = f"克隆异常: {str(e)}"
            logger.error(error_msg)
            return TaskResult(success=False, message=error_msg)

    def _normalize_repo_url(self, repo_url: str) -> str:
        """将 shorthand 格式转换为完整 HTTPS URL"""
        # 如果已经是完整 URL，直接返回
        if repo_url.startswith("http://") or repo_url.startswith("https://"):
            return repo_url

        # 如果是 git@ 格式（SSH），转换为 HTTPS
        if repo_url.startswith("git@"):
            repo_url = repo_url.replace("git@github.com:", "")
            return f"https://github.com/{repo_url}"

        # shorthand 格式（如 "owner/repo"）转换为完整 URL
        github_token = os.getenv("GITHUB_TOKEN", "")
        if "/" in repo_url:
            if github_token:
                return f"https://{github_token}@github.com/{repo_url}.git"
            else:
                return f"https://github.com/{repo_url}.git"

        return repo_url
