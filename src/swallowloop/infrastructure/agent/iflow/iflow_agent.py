"""IFlow Agent 实现"""

import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from iflow_sdk import (
    IFlowClient,
    IFlowOptions,
    AssistantMessage,
    TaskFinishMessage,
    ToolCallMessage,
    ApprovalMode,
)

from ..base import Agent, ExecutionResult
from ....domain.model import Task, TaskType


@dataclass
class IFlowConfig:
    """IFlow 配置"""
    timeout: float = 600.0
    approval_mode: ApprovalMode = ApprovalMode.YOLO
    file_access: bool = True
    file_read_only: bool = False
    log_level: str = "INFO"
    auth_method_id: str | None = None
    auth_method_info: dict[str, Any] | None = None


class IFlowAgent(Agent):
    """
    IFlow Agent 实现
    
    使用 iFlow CLI SDK 进行代码开发
    """
    
    def __init__(self, config: IFlowConfig | None = None):
        self._config = config or IFlowConfig()
    
    @property
    def name(self) -> str:
        return "iflow"
    
    def execute(
        self,
        task: Task,
        workspace_path: Path,
    ) -> ExecutionResult:
        """执行任务（同步包装）"""
        return asyncio.run(self._execute_async(task, workspace_path))
    
    async def _execute_async(
        self,
        task: Task,
        workspace_path: Path,
    ) -> ExecutionResult:
        """异步执行任务"""
        if task.task_type == TaskType.NEW_TASK:
            return await self._execute_new_task(task, workspace_path)
        else:
            return await self._execute_revision(task, workspace_path)
    
    async def _execute_new_task(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """
        执行新任务
        
        流程：
        1. 检查/克隆仓库
        2. 创建分支
        3. 运行 iFlow
        4. 提交并推送
        """
        # 1. 准备仓库
        prep_result = self._prepare_repo(task, workspace_path)
        if not prep_result.success:
            return prep_result
        
        # 2. 创建或切换分支
        branch_result = self._setup_branch(task, workspace_path)
        if not branch_result.success:
            return branch_result
        
        # 3. 运行 iFlow
        task_prompt = self._build_prompt(task)
        result = await self._run_iflow(workspace_path, task_prompt)
        
        if not result.success:
            return result
        
        # 4. 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(
                success=False,
                message="iFlow 未修改任何文件",
            )
        
        commit_result = self._commit_and_push(task, workspace_path, files_changed)
        return commit_result
    
    async def _execute_revision(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """
        执行修改任务
        
        流程：
        1. 切换到现有分支
        2. 拉取最新代码
        3. 运行 iFlow
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
        
        # 2. 运行 iFlow
        task_prompt = self._build_prompt(task)
        result = await self._run_iflow(workspace_path, task_prompt)
        
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
    
    def _prepare_repo(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """准备仓库"""
        # 确保工作空间目录存在
        workspace_path.mkdir(parents=True, exist_ok=True)
        
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
                    ["git", "clone", task.repo_url, "."],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                return ExecutionResult(
                    success=False,
                    message=f"克隆仓库失败: {e.stderr.decode() if e.stderr else str(e)}",
                )
        return ExecutionResult(success=True, message="仓库准备完成")
    
    def _setup_branch(self, task: Task, workspace_path: Path) -> ExecutionResult:
        """设置分支"""
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
        return ExecutionResult(success=True, message="分支设置完成")
    
    async def _run_iflow(self, repo_path: Path, prompt: str) -> ExecutionResult:
        """运行 iFlow"""
        options = IFlowOptions(
            timeout=self._config.timeout,
            approval_mode=self._config.approval_mode,
            file_access=self._config.file_access,
            file_read_only=self._config.file_read_only,
            log_level=self._config.log_level,
            cwd=str(repo_path),
            auth_method_id=self._config.auth_method_id,
            auth_method_info=self._config.auth_method_info,
        )
        
        output_parts = []
        
        try:
            async with IFlowClient(options) as client:
                await client.send_message(prompt)
                
                async for message in client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        output_parts.append(message.chunk.text)
                    elif isinstance(message, ToolCallMessage):
                        output_parts.append(
                            f"[工具调用] {message.tool_name or message.label}: {message.status}"
                        )
                    elif isinstance(message, TaskFinishMessage):
                        break
            
            output = "".join(output_parts)
            return ExecutionResult(
                success=True,
                message="iFlow 完成",
                output=output,
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"iFlow 执行失败: {str(e)}",
                output="".join(output_parts),
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
    
    def _commit_and_push(
        self,
        task: Task,
        workspace_path: Path,
        files_changed: list[str],
    ) -> ExecutionResult:
        """提交并推送"""
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
        )
    
    def _build_prompt(self, task: Task) -> str:
        """构建任务提示"""
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
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        """检查 iFlow 是否可用"""
        try:
            import iflow_sdk
            return True, f"iflow-cli-sdk v{iflow_sdk.__version__}"
        except ImportError:
            return False, "iflow-cli-sdk 未安装，请执行: pip install iflow-cli-sdk"
