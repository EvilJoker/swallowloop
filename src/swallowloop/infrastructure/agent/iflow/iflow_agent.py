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
    timeout: float = 1200.0  # Agent 超时时间（秒），默认 20 分钟
    approval_mode: ApprovalMode = ApprovalMode.YOLO
    file_access: bool = True
    file_read_only: bool = False
    log_level: str = "INFO"
    auth_method_id: str | None = None
    auth_method_info: dict[str, Any] | None = None
    base_port: int = 8090  # iFlow 进程基础端口，实际端口 = base_port + (issue_number % 100)


class IFlowAgent(Agent):
    """IFlow Agent 实现 - 使用 iFlow CLI SDK 进行代码开发"""
    
    # 端口分配锁，防止并发分配相同端口
    _port_lock = asyncio.Lock()
    _used_ports: set[int] = set()
    
    def __init__(
        self,
        config: IFlowConfig | None = None,
        settings: "Settings | None" = None,
    ):
        self._settings = settings
        self._codebase_manager: "CodebaseManager | None" = None
        self._current_port: int | None = None  # 当前使用的端口
        
        # 如果没有传入 config，从 settings 构建
        if config is None and settings:
            # 从 LLMConfig 获取认证信息
            llm_config = settings.get_llm_config()
            self._config = IFlowConfig(
                timeout=float(settings.agent_timeout),
                auth_method_id=llm_config.iflow_auth_method_id,
                auth_method_info=llm_config.to_iflow_auth_info(),
            )
        else:
            self._config = config or IFlowConfig()
        
        if settings:
            from ...codebase import CodebaseManager
            self._codebase_manager = CodebaseManager(
                codebase_dir=settings.codebase_dir,
                github_repo=settings.github_repo,
            )
    
    @property
    def name(self) -> str:
        return "iflow"
    
    def _allocate_port(self, issue_number: int) -> int:
        """为 Worker 分配唯一的 iFlow 端口
        
        端口分配策略：base_port + (issue_number % 100)
        支持 100 个并发 Worker (端口 8090-8189)
        """
        port = self._config.base_port + (issue_number % 100)
        self._current_port = port
        print(f"[Agent] 分配 iFlow 端口: {port} (Issue#{issue_number})")
        return port
    
    def execute(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 分配端口
        self._allocate_port(task.issue_number)
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
        
        # 4. 获取修改的文件
        files_changed = self._get_changed_files(workspace_path)
        print(f"[Agent] 检测到修改的文件: {files_changed}")
        
        if not files_changed:
            return ExecutionResult(False, "iFlow 未修改任何文件")
        
        # 5. 使用 AI 生成 commit message
        diff = self._get_diff(workspace_path)
        commit_message = await self._generate_commit_message(workspace_path, diff, task)
        print(f"[Agent] AI 生成的 commit message: {commit_message}")
        
        # 6. 提交推送
        result = self._commit_and_push_with_message(task, workspace_path, files_changed, commit_message)
        print(f"[Agent] 提交推送结果: success={result.success}, message={result.message}")
        return result
    
    async def _execute_revision(self, task: Task, workspace_path: Path) -> ExecutionResult:
        # 1. 切换分支
        result = self._prepare_revision(task, workspace_path)
        if not result.success:
            return result
        
        # 2. 运行 iFlow
        result = await self._run_iflow(workspace_path, self._build_prompt(task))
        if not result.success:
            return result
        
        # 3. 获取修改的文件
        files_changed = self._get_changed_files(workspace_path)
        if not files_changed:
            return ExecutionResult(True, "无需修改")
        
        # 4. 使用 AI 生成 commit message
        diff = self._get_diff(workspace_path)
        commit_message = await self._generate_commit_message(workspace_path, diff, task)
        print(f"[Agent] AI 生成的 commit message: {commit_message}")
        
        # 5. Amend 提交
        return self._commit_and_push_with_message(task, workspace_path, files_changed, commit_message)
    
    async def _run_iflow(self, repo_path: Path, prompt: str) -> ExecutionResult:
        """运行 iFlow"""
        port = self._current_port or self._config.base_port
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
            process_start_port=port,  # 使用分配的端口
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
    
    async def _generate_commit_message(self, repo_path: Path, diff: str, task: Task) -> str:
        """使用 AI 生成 commit message
        
        Args:
            repo_path: 仓库路径
            diff: git diff 内容
            task: 任务对象
            
        Returns:
            生成的 commit message，格式: {type}: {description}
        """
        prompt = f"""请根据以下代码变更生成一个简洁的 commit message。

## 规则
1. 格式: `{{type}}: {{description}}`
2. type 只能是: feat, fix, docs, style, refactor, test, chore
3. description 是简短的中文描述，不超过 30 字
4. 只输出 commit message，不要其他内容

## 原始任务
{task.title}

## 代码变更
```diff
{diff[:8000]}
```

请生成 commit message:"""
        
        port = self._current_port or self._config.base_port
        options = IFlowOptions(
            timeout=30.0,  # 短超时，生成 commit message 很快
            approval_mode=self._config.approval_mode,
            file_access=False,  # 不需要文件访问
            file_read_only=True,
            log_level=self._config.log_level,
            cwd=str(repo_path),
            auth_method_id=self._config.auth_method_id,
            auth_method_info=self._config.auth_method_info,
            process_start_port=port,  # 使用相同的端口
        )
        
        try:
            async with IFlowClient(options) as client:
                await client.send_message(prompt)
                result = ""
                async for message in client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        result += message.chunk.text
                    elif isinstance(message, TaskFinishMessage):
                        break
                
                # 清理输出，提取 commit message
                commit_msg = result.strip()
                # 移除可能的 markdown 代码块标记
                if commit_msg.startswith("```"):
                    commit_msg = commit_msg.split("\n", 1)[-1]
                if commit_msg.endswith("```"):
                    commit_msg = commit_msg.rsplit("```", 1)[0]
                
                # 验证格式，如果不符合则使用默认格式
                if not any(commit_msg.startswith(f"{t}:") for t in ["feat", "fix", "docs", "style", "refactor", "test", "chore"]):
                    # 根据任务类型生成默认消息
                    return f"feat: {task.title[:30]}"
                
                return commit_msg.strip()
        except Exception as e:
            print(f"[Agent] 生成 commit message 失败: {e}，使用默认格式")
            return f"feat: {task.title[:30]}"
    
    @staticmethod
    def check_available() -> tuple[bool, str]:
        try:
            import iflow_sdk
            return True, f"iflow-cli-sdk v{iflow_sdk.__version__}"
        except ImportError:
            return False, "iflow-cli-sdk 未安装，请执行: pip install iflow-cli-sdk"
    
    @classmethod
    def _get_diff(cls, workspace_path: Path) -> str:
        """获取 git diff（相对于 main 分支的总修改）
        
        设计原则：一个任务一个 commit
        所以 diff 是整个分支相对于 base 的所有修改
        """
        try:
            # 获取相对于 main 的 diff
            result = cls._run_git(["diff", "main"], workspace_path, check=False)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            
            # 如果 main 不存在，尝试 master
            result = cls._run_git(["diff", "master"], workspace_path, check=False)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            
            # 如果都没有（新分支，还没 commit），获取工作区 diff
            result = cls._run_git(["diff"], workspace_path, check=False)
            return result.stdout
        except Exception:
            return ""
    
    @classmethod
    def _commit_and_push_with_message(
        cls,
        task: Task,
        workspace_path: Path,
        files_changed: list[str],
        commit_message: str,
    ) -> ExecutionResult:
        """使用指定的 commit message 提交并推送"""
        import subprocess
        
        # 检查当前分支是否正确
        try:
            result = cls._run_git(["branch", "--show-current"], workspace_path)
            current_branch = result.stdout.strip()
            print(f"[Git] 当前分支: {current_branch}, 目标分支: {task.branch_name}")
            
            if current_branch != task.branch_name:
                print(f"[Git] 分支不匹配，尝试切换到 {task.branch_name}")
                result = cls._run_git(["checkout", task.branch_name], workspace_path, check=False)
                if result.returncode != 0:
                    print(f"[Git] 分支不存在，创建新分支 {task.branch_name}")
                    cls._run_git(["checkout", "-b", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"分支检查失败: {e.stderr or str(e)}", files_changed)
        
        # 检查分支上是否已有自己的 commit
        has_own_commit = cls._has_own_commit(workspace_path)
        
        try:
            print(f"[Git] 添加文件到暂存区...")
            cls._run_git(["add", "-A"], workspace_path)
            
            if has_own_commit:
                print(f"[Git] Amend 提交: {commit_message}")
                cls._run_git(["commit", "--amend", "-m", commit_message], workspace_path)
            else:
                print(f"[Git] 创建提交: {commit_message}")
                cls._run_git(["commit", "-m", commit_message], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"提交失败: {e.stderr or str(e)}", files_changed)
        
        try:
            print(f"[Git] 推送分支到远程: {task.branch_name}")
            result = cls._run_git(
                ["ls-remote", "--heads", "origin", task.branch_name],
                workspace_path,
                check=False
            )
            remote_exists = bool(result.stdout.strip())
            
            if remote_exists or has_own_commit:
                print(f"[Git] 强制推送（已有远程分支）")
                cls._run_git(["push", "-f", "origin", task.branch_name], workspace_path)
            else:
                cls._run_git(["push", "-u", "origin", task.branch_name], workspace_path)
            print(f"[Git] 推送成功: {task.branch_name}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or str(e)
            print(f"[Git] 推送失败: {error_msg}")
            return ExecutionResult(False, f"推送失败: {error_msg}", files_changed)
        
        return ExecutionResult(True, "任务完成，等待 PR 创建", files_changed, commit_message=commit_message)