"""环境准备 - 准备环境任务"""

import subprocess
import os
from ..task import Task, TaskResult


class EnvironmentPrepareEnvTask(Task):
    """环境准备 - 准备环境任务"""

    def __init__(self):
        super().__init__(
            name="准备环境",
            handler=self._execute,
            description="安装项目依赖"
        )

    def _execute(self, context: dict) -> TaskResult:
        """执行准备环境"""
        # 优先使用 repo_path（克隆任务设置的），否则使用 workspace_path
        repo_path = context.get("repo_path") or context.get("workspace_path")

        if not repo_path:
            return TaskResult(success=False, message="repo_path 未指定")

        try:
            # 检测项目类型并安装依赖
            if os.path.exists(os.path.join(repo_path, "requirements.txt")):
                # Python 项目
                result = subprocess.run(
                    ["pip", "install", "-r", "requirements.txt"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            elif os.path.exists(os.path.join(repo_path, "package.json")):
                # Node.js 项目
                result = subprocess.run(
                    ["npm", "install"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            elif os.path.exists(os.path.join(repo_path, "pyproject.toml")):
                # Python uv 项目
                result = subprocess.run(
                    ["uv", "pip", "install", "-e", "."],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            else:
                return TaskResult(success=True, message="未检测到依赖文件，跳过")

            if result.returncode == 0:
                return TaskResult(success=True, message="环境准备完成")
            else:
                return TaskResult(success=False, message=f"安装依赖失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            return TaskResult(success=False, message="安装依赖超时")
        except Exception as e:
            return TaskResult(success=False, message=f"准备环境异常: {str(e)}")
