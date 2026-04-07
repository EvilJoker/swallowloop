"""Issue Pipeline - 包含所有 Stage 执行逻辑"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...infrastructure.agent import BaseAgent

from .context import PipelineContext
from .pipeline import Pipeline, PipelineStatus, PipelineState
from .environment_stage.environment_stage import EnvironmentStage
from .brainstorm_stage.brainstorm_stage import BrainstormStage
from .plan_formed_stage.plan_formed_stage import PlanFormedStage
from .detailed_design_stage.detailed_design_stage import DetailedDesignStage
from .task_split_stage.task_split_stage import TaskSplitStage
from .execution_stage.execution_stage import ExecutionStage
from .update_docs_stage.update_docs_stage import UpdateDocsStage
from .submit_stage.submit_stage import SubmitStage

logger = logging.getLogger(__name__)


# 内置阶段指令
STAGE_INSTRUCTIONS: dict[str, str] = {
    "brainstorm": """请对这个问题进行头脑风暴：

1. 分析问题的背景和需求
2. 提出 3-5 个可能的解决方案
3. 评估每个方案的优缺点
4. 给出推荐方案及理由

输出格式：
- 解决方案列表（带序号）
- 每个方案的优缺点
- 推荐方案及理由""",
}


class IssuePipeline(Pipeline):
    """Issue Pipeline - 包含所有 Stage 执行逻辑

    每个阶段只操作 self.context，完全解耦
    """

    def __init__(self, issue_id: str = "", issue_title: str = "", issue_description: str = "",
                 repo_url: str = "", repo_branch: str = "main"):
        super().__init__(name="issue-pipeline")
        self._context = PipelineContext(
            issue_id=issue_id,
            workspace_path="",
            repo_url=repo_url,
            repo_name="repo",
            branch=repo_branch,
        )
        # 额外字段存储 issue_title 和 issue_description
        self._context.extra = {
            "issue_title": issue_title,
            "issue_description": issue_description,
        }
        self._stages = [
            EnvironmentStage(),
            BrainstormStage(),
            PlanFormedStage(),
            DetailedDesignStage(),
            TaskSplitStage(),
            ExecutionStage(),
            UpdateDocsStage(),
            SubmitStage(),
        ]
        # agent 引用
        self._agent = None
        # Pipeline 状态
        self._status = PipelineStatus(state=PipelineState.PENDING, reason="待执行")

    def set_agent(self, agent: "BaseAgent"):
        """设置 agent（用于执行任务）"""
        self._agent = agent

    def get_context(self) -> PipelineContext:
        """获取 PipelineContext（只读）"""
        return self._context

    def set_context_value(self, key: str, value):
        """设置 context 中的字段值

        Args:
            key: 字段名（如 "workspace_path", "repo_url"）
            value: 字段值
        """
        if hasattr(self._context, key):
            setattr(self._context, key, value)
        elif key in self._context.extra:
            self._context.extra[key] = value
        else:
            raise KeyError(f"未知的 context 字段: {key}")

    def get_status(self) -> PipelineStatus:
        """获取当前执行状态

        返回 PipelineStatus，包含:
        - state: 执行状态
        - reason: 状态描述
        - current_stage: 当前执行的 stage 名称
        - current_task: 当前执行的 task 名称
        - stages_status: 所有 stage 的状态列表
        """
        # 更新 stages_status
        self._status.stages_status = [stage.status for stage in self._stages]
        return self._status

    def execute_environment(self) -> dict:
        """执行环境准备阶段

        从 self._context 读取 repo_url, repo_branch
        执行后更新 self._context（workspace_path 等）

        返回值包含:
        - success: 是否成功
        - message: 状态消息
        - stage_status: StageStatus 对象（用于前端展示）
        """
        logger.info("执行环境准备阶段...")

        # 更新 PipelineStatus
        self._status.state = PipelineState.RUNNING
        self._status.current_stage = "environment"
        self._status.current_task = ""
        self._status.reason = "执行环境准备阶段"

        # 执行 environment stage 的 tasks
        stage_obj = self._stages[0]  # environment 是第一个 stage
        context_dict = self._context.to_dict()

        # 注入 agent 到需要它的 task
        if self._agent:
            for task in stage_obj.tasks:
                if hasattr(task, 'set_agent'):
                    task.set_agent(self._agent)

        # 使用 stage.execute() 统一执行，它会更新 stage.status
        context_dict, task_result = stage_obj.execute(context_dict)
        all_success = task_result.success

        # 更新 PipelineStatus
        self._status.state = PipelineState.COMPLETED if all_success else PipelineState.FAILED
        self._status.reason = task_result.message

        # 用执行结果更新 self._context
        if context_dict.get("workspace_path"):
            self._context.workspace_path = context_dict["workspace_path"]
        if context_dict.get("repo_name"):
            self._context.repo_name = context_dict["repo_name"]
        if context_dict.get("thread_id"):
            self._context.thread_id = context_dict["thread_id"]

        return {
            "success": all_success,
            "message": task_result.message,
            "stage_status": stage_obj.status,  # 返回 StageStatus 给前端
        }

    def execute_brainstorm(self) -> dict:
        """执行头脑风暴阶段

        从 self._context 读取环境信息，调用 DeerFlow 执行
        执行后更新 self._context（brainstorm_output 等）
        """
        logger.info("执行头脑风暴阶段...")

        if not self._agent:
            return {"success": False, "error": "agent 未设置"}

        # 获取 workspace 信息
        workspace_path = self._context.workspace_path
        thread_id = self._context.thread_id
        repo_url = self._context.repo_url
        repo_branch = self._context.branch
        issue_id = self._context.issue_id
        issue_title = self._context.extra.get("issue_title", "")
        issue_description = self._context.extra.get("issue_description", "")

        if not workspace_path:
            return {"success": False, "error": "workspace_path 未设置"}

        # 生成 stage 文件
        stage_file = Path(workspace_path) / "brainstorm.md"
        result_file = Path(workspace_path) / "brainstorm-result.json"

        # 读取内置指令
        instruction = """请对这个问题进行头脑风暴：

1. 分析问题的背景和需求
2. 提出 3-5 个可能的解决方案
3. 评估每个方案的优缺点
4. 给出推荐方案及理由

输出格式：
- 解决方案列表（带序号）
- 每个方案的优缺点
- 推荐方案及理由"""

        # 构建 context 文件内容
        context_content = f"""# Stage brainstorm

## Issue 信息
- 标题: {issue_title}
- 描述: {issue_description or "无"}
- ID: {issue_id}

## 环境信息（来自 pipeline.context）
- 仓库: {repo_url or "N/A"}
- 分支: {repo_branch or "N/A"}
- Issue 分支: {issue_id}
- 仓库路径: {workspace_path}

## 阶段指令
{instruction}

## 期望输出
完成 brainstorm 任务后，将结果写入 brainstorm-result.json
结果使用 JSON 格式：
{{
  "status": "success" | "failed",
  "output": "执行摘要",
  "files": ["生成的文件列表"],
  "error": "错误信息（如果有）"
}}
"""

        stage_file.write_text(context_content, encoding="utf-8")

        # 构建任务消息
        task_message = f"""请读取并执行任务文件 {stage_file}，完成后将结果写入 {result_file}。"""

        context = {
            "thread_id": thread_id,
            "stage_file": str(stage_file),
            "result_file": str(result_file),
        }

        # 调用 DeerFlow 执行
        import asyncio
        result = asyncio.run(self._agent.execute(task_message, context))

        # 读取结果
        if result.success:
            try:
                if result_file.exists():
                    import json
                    with open(result_file, "r", encoding="utf-8") as f:
                        result_data = json.load(f)
                        self._context.stages_context["brainstorm_output"] = result_data.get("output", result.output or "")
                    result_file.unlink(missing_ok=True)
                else:
                    self._context.stages_context["brainstorm_output"] = result.output or ""
            except Exception as e:
                logger.warning(f"读取 brainstorm-result.json 失败: {e}")
                self._context.stages_context["brainstorm_output"] = result.output or ""

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        }


# 公开 API（控制 from swallowloop.domain.pipeline.issue_pipeline import * 的导出）
__all__ = [
    "IssuePipeline",
    "execute_environment",
    "get_status",
    "get_context",
    "set_context_value",
    "set_agent",
]
