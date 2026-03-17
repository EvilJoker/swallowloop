"""IFlow Agent 实现"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

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

if TYPE_CHECKING:
    from ...config import Settings
    from ...codebase import CodebaseManager


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
    """IFlow Agent 实现 - 使用 iFlow CLI SDK 进行代码开发"""
    
    def __init__(
        self,
        config: IFlowConfig | None = None,
        settings: "Settings | None" = None,
    ):
        self._config = config or IFlowConfig()
        self._settings = settings
        self._codebase_manager: "CodebaseManager | None" = None
        
        if settings:
            from ...codebase import CodebaseManager
            self._codebase_manager = CodebaseManager(
                codebase_dir=settings.codebase_dir,
                github_repo=settings.github_repo,
            )
    
    @property
    def name(self) -> str:
        return "iflow"
    
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        return asyncio.run(self._execute_async(task, workspace_path))
    
    async def _execute_async(self, task: Task, workspace_path: Path) -> ExecutionResult:
        if task.task_type == TaskType.NEW_TASK:
            return await self._execute_new_task(task, workspace_path)
        else:
            return await self._execute_revision(task, workspace_path)
    
    async def _execute_new_task(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 1. 准备仓库
        result = self._prepare_repo(
            task,
            workspace_path,
            codebase_manager=self._codebase_manager,
            github_token=self._settings.github_token if self._settings else None,
        )
        if not result.success:
            return result
        
        # 2. 设置分支
        result = self._setup_branch(task, workspace_path)
        if not result.success:
            return result
        
        # 3. 运行 iFlow
        result = await self._run_iflow(workspace_path, self._build_prompt(task))
        if not result.success:
            return result
        
        # 4. 提交推送
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(False, "iFlow 未修改任何文件")
        
        return self._commit_and_push(task, workspace_path, files_changed)
    
    async def _execute_revision(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 1. 切换分支
        result = self._prepare_revision(task, workspace_path)
        if not result.success:
            return result
        
        # 2. 运行 iFlow
        result = await self._run_iflow(workspace_path, self._build_prompt(task))
        if not result.success:
            return result
        
        # 3. Amend 提交
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(True, "无需修改")
        
        return self._amend_and_push(task, workspace_path, files_changed)
    
    async def _run_iflow(self, repo_path: Path, prompt: str) -> ExecutionResult:
        """运行 iFlow"""
        options = IFlowOptions(
            timeout=self._config.timeout,
            approval_mode=self._config.approval_mode,
            file_access=self._config.file_access,
            file_allowed_dirs=[str(repo_path)],  # 显式设置允许访问的目录
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
                        output_parts.append(f"[工具调用] {message.tool_name or message.label}: {message.status}")
                    elif isinstance(message, TaskFinishMessage):
                        break
            
            return ExecutionResult(True, "iFlow 完成", output="".join(output_parts))
        except Exception as e:
            return ExecutionResult(False, f"iFlow 执行失败: {str(e)}", output="".join(output_parts))
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        try:
            import iflow_sdk
            return True, f"iflow-cli-sdk v{iflow_sdk.__version__}"
        except ImportError:
            return False, "iflow-cli-sdk 未安装，请执行: pip install iflow-cli-sdk"