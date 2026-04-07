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
    "planFormed": """请根据头脑风暴的结果，制定详细方案：

1. 确定最终推荐的解决方案
2. 给出详细的实施步骤
3. 预估时间和资源需求
4. 识别潜在风险和应对措施

输出格式：
- 推荐方案
- 详细实施步骤
- 时间预估
- 风险评估""",
    "detailedDesign": """请进行详细设计：

1. 定义数据结构和接口
2. 设计模块结构和职责
3. 制定关键算法
4. 考虑边界情况和错误处理

输出格式：
- 数据结构设计
- 模块设计
- 关键算法
- 边界情况""",
    "taskSplit": """请将任务拆分为可执行的小任务：

1. 列出所有需要执行的子任务
2. 确定任务间的依赖关系
3. 预估每个子任务的复杂度

输出格式：
- 子任务列表（带序号和描述）
- 依赖关系
- 复杂度评估""",
    "execution": """请执行任务：

1. 按照计划执行任务
2. 记录执行过程中的关键发现
3. 解决遇到的问题
4. 保持代码质量

输出格式：
- 执行进度
- 关键发现
- 遇到的问题及解决方案
- 代码变更""",
    "updateDocs": """请更新文档：

1. 更新必要的代码文档
2. 更新 README 或其他项目文档
3. 确保文档与代码一致

输出格式：
- 更新的文档列表
- 关键变更说明""",
    "submit": """请提交代码：

1. 确保所有更改已提交
2. 创建 PR（如果适用）
3. 列出所有变更

输出格式：
- 变更摘要
- PR 链接（如果有）
- 后续待办""",
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

    async def execute_stage(self, stage_name: str) -> dict:
        """执行指定阶段

        - 如果阶段有 tasks，执行 tasks
        - 如果阶段没有 tasks（空实现），直接调用 agent 执行阶段指令
        - 更新 self._context

        Args:
            stage_name: 阶段名称（如 "brainstorm", "planFormed"）

        Returns:
            dict with keys: success, message, stage_status
        """
        logger.info(f"执行阶段: {stage_name}")

        # 更新 PipelineStatus
        self._status.state = PipelineState.RUNNING
        self._status.current_stage = stage_name
        self._status.current_task = ""
        self._status.reason = f"执行 {stage_name} 阶段"

        # 找到对应的 stage 对象
        stage_obj = None
        for s in self._stages:
            if s.name == stage_name:
                stage_obj = s
                break

        if stage_obj is None:
            logger.error(f"未找到阶段: {stage_name}")
            return {
                "success": False,
                "message": f"未找到阶段: {stage_name}",
                "stage_status": None,
            }

        # 如果阶段有 tasks，执行 tasks
        if stage_obj.tasks:
            context_dict = self._context.to_dict()
            # 注入 agent 到需要它的 task
            if self._agent:
                for task in stage_obj.tasks:
                    if hasattr(task, 'set_agent'):
                        task.set_agent(self._agent)
            context_dict, task_result = stage_obj.execute(context_dict)
            all_success = task_result.success

            # 更新 PipelineStatus
            self._status.state = PipelineState.COMPLETED if all_success else PipelineState.FAILED
            self._status.reason = task_result.message

            # 更新 context
            if context_dict.get("workspace_path"):
                self._context.workspace_path = context_dict["workspace_path"]
            if context_dict.get("repo_name"):
                self._context.repo_name = context_dict["repo_name"]
            if context_dict.get("thread_id"):
                self._context.thread_id = context_dict["thread_id"]

            return {
                "success": all_success,
                "message": task_result.message,
                "stage_status": stage_obj.status,
            }

        # 空实现阶段：直接调用 agent 执行阶段指令
        if not self._agent:
            logger.error("Agent 未配置")
            return {
                "success": False,
                "message": "Agent 未配置",
                "stage_status": stage_obj.status,
            }

        # 获取阶段指令
        instruction = STAGE_INSTRUCTIONS.get(stage_name, "")
        if not instruction:
            logger.warning(f"阶段 {stage_name} 没有内置指令")
            instruction = f"请执行 {stage_name} 阶段的任务"

        # 构建任务指令
        issue_title = self._context.extra.get("issue_title", "")
        issue_description = self._context.extra.get("issue_description", "")
        task_message = f"""# Issue 信息
标题: {issue_title}
描述: {issue_description}

# 任务
{instruction}

请完成任务后将结果以 JSON 格式返回：
{{
  "status": "success" | "failed",
  "output": "执行结果摘要",
  "error": "错误信息（如果有）"
}}"""

        context = {
            "thread_id": self._context.thread_id,
            "stage": stage_name,
        }

        logger.info(f"调用 Agent 执行阶段 {stage_name}: thread_id={self._context.thread_id}")

        # 调用 Agent 执行
        result = await self._agent.execute(task_message, context)

        # 更新 PipelineStatus
        self._status.state = PipelineState.COMPLETED if result.success else PipelineState.FAILED
        self._status.reason = result.output or result.error or ""

        return {
            "success": result.success,
            "message": result.output or result.error or "",
            "output": result.output,
            "error": result.error,
            "stage_status": stage_obj.status,
        }


# 公开 API（控制 from swallowloop.domain.pipeline.issue_pipeline import * 的导出）
__all__ = [
    "IssuePipeline",
    "execute_environment",
    "execute_stage",
    "get_status",
    "get_context",
    "set_context_value",
    "set_agent",
]
