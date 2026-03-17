"""IFlow Agent 实现"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

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
        log_callback: Callable[[str], None] | None = None,
    ):
        self._config = config or IFlowConfig()
        self._settings = settings
        self._codebase_manager: "CodebaseManager | None" = None
        self._log_callback = log_callback
        
        if settings:
            from ...codebase import CodebaseManager
            self._codebase_manager = CodebaseManager(
                codebase_dir=settings.codebase_dir,
                github_repo=settings.github_repo,
            )
    
    @property
    def name(self) -> str:
        return "iflow"
    
    def _log(self, message: str, log_file: Path | None = None) -> None:
        """输出日志到文件和回调"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        
        # 写入文件
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
                f.flush()
                os.fsync(f.fileno())
        
        # 调用回调
        if self._log_callback:
            self._log_callback(log_line)
    
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 确定日志文件路径
        log_file = None
        if self._settings and self._settings.logs_dir:
            log_file = self._settings.logs_dir / f"issue_{task.issue_number}.log"
        
        return asyncio.run(self._execute_async(task, workspace_path, log_file))
    
    async def _execute_async(self, task: Task, workspace_path: Path, log_file: Path | None = None) -> ExecutionResult:
        self._log(f"=== 开始执行任务 Issue#{task.issue_number} ===", log_file)
        self._log(f"标题: {task.title}", log_file)
        self._log(f"类型: {task.task_type.value}", log_file)
        self._log(f"工作空间: {workspace_path}", log_file)
        
        if task.task_type == TaskType.NEW_TASK:
            return await self._execute_new_task(task, workspace_path, log_file)
        else:
            return await self._execute_revision(task, workspace_path, log_file)
    
    async def _execute_new_task(self, task: Task, workspace_path: Path, log_file: Path | None = None) -> ExecutionResult:
        # 1. 准备仓库
        self._log("[步骤 1/4] 准备仓库...", log_file)
        result = self._prepare_repo(
            task,
            workspace_path,
            codebase_manager=self._codebase_manager,
            github_token=self._settings.github_token if self._settings else None,
        )
        if not result.success:
            self._log(f"[错误] 准备仓库失败: {result.message}", log_file)
            return result
        self._log(f"[成功] {result.message}", log_file)
        
        # 2. 设置分支
        self._log("[步骤 2/4] 设置分支...", log_file)
        result = self._setup_branch(task, workspace_path)
        if not result.success:
            self._log(f"[错误] 设置分支失败: {result.message}", log_file)
            return result
        self._log(f"[成功] 分支: {task.branch_name}", log_file)
        
        # 3. 运行 iFlow
        self._log("[步骤 3/4] 运行 iFlow...", log_file)
        result = await self._run_iflow(workspace_path, self._build_prompt(task), log_file)
        if not result.success:
            self._log(f"[错误] iFlow 执行失败: {result.message}", log_file)
            return result
        self._log("[成功] iFlow 执行完成", log_file)
        
        # 4. 提交推送
        self._log("[步骤 4/4] 提交推送...", log_file)
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            self._log("[警告] iFlow 未修改任何文件", log_file)
            return ExecutionResult(False, "iFlow 未修改任何文件")
        
        result = self._commit_and_push(task, workspace_path, files_changed)
        if result.success:
            self._log(f"[成功] 已提交 {len(files_changed)} 个文件", log_file)
            self._log(f"=== 任务执行完成 ===", log_file)
        else:
            self._log(f"[错误] 提交推送失败: {result.message}", log_file)
        return result
    
    async def _execute_revision(self, task: Task, workspace_path: Path, log_file: Path | None = None) -> ExecutionResult:
        # 1. 切换分支
        self._log("[步骤 1/3] 切换分支...", log_file)
        result = self._prepare_revision(task, workspace_path)
        if not result.success:
            self._log(f"[错误] 切换分支失败: {result.message}", log_file)
            return result
        self._log(f"[成功] 分支: {task.branch_name}", log_file)
        
        # 2. 运行 iFlow
        self._log("[步骤 2/3] 运行 iFlow (修订)...", log_file)
        result = await self._run_iflow(workspace_path, self._build_prompt(task), log_file)
        if not result.success:
            self._log(f"[错误] iFlow 执行失败: {result.message}", log_file)
            return result
        self._log("[成功] iFlow 执行完成", log_file)
        
        # 3. Amend 提交
        self._log("[步骤 3/3] Amend 提交...", log_file)
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            self._log("[信息] 无需修改", log_file)
            return ExecutionResult(True, "无需修改")
        
        result = self._amend_and_push(task, workspace_path, files_changed)
        if result.success:
            self._log(f"[成功] 已修改 {len(files_changed)} 个文件", log_file)
            self._log(f"=== 任务执行完成 ===", log_file)
        else:
            self._log(f"[错误] 提交失败: {result.message}", log_file)
        return result
    
    async def _run_iflow(self, repo_path: Path, prompt: str, log_file: Path | None = None) -> ExecutionResult:
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
                        text = message.chunk.text
                        output_parts.append(text)
                        self._log(f"[AI] {text}", log_file)
                    elif isinstance(message, ToolCallMessage):
                        tool_info = f"[工具调用] {message.tool_name or message.label}: {message.status}"
                        output_parts.append(tool_info)
                        self._log(tool_info, log_file)
                    elif isinstance(message, TaskFinishMessage):
                        self._log("[iFlow] 任务完成", log_file)
                        break
            
            return ExecutionResult(True, "iFlow 完成", output="".join(output_parts))
        except Exception as e:
            error_msg = f"iFlow 执行失败: {str(e)}"
            self._log(f"[错误] {error_msg}", log_file)
            return ExecutionResult(False, error_msg, output="".join(output_parts))
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        try:
            import iflow_sdk
            return True, f"iflow-cli-sdk v{iflow_sdk.__version__}"
        except ImportError:
            return False, "iflow-cli-sdk 未安装，请执行: pip install iflow-cli-sdk"