"""Issue Pipeline - 包含所有 Stage 执行逻辑"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...infrastructure.agent import BaseAgent

from .context import PipelineContext
from .pipeline import Pipeline, PipelineStatus, PipelineState
from .environment_stage.environment_stage import EnvironmentStage
from .specify_stage.specify_stage import SpecifyStage
from .clarify_stage.clarify_stage import ClarifyStage
from .plan_stage.plan_stage import PlanStage
from .checklist_stage.checklist_stage import ChecklistStage
from .tasks_stage.tasks_stage import TasksStage
from .analyze_stage.analyze_stage import AnalyzeStage
from .implement_stage.implement_stage import ImplementStage
from .submit_stage.submit_stage import SubmitStage

logger = logging.getLogger(__name__)


# SDD 阶段指令（备用，如果 stage 没有实现 Task）
STAGE_INSTRUCTIONS: dict[str, str] = {
    "specify": """请对 Issue 进行规范定义：

1. 明确需求范围和目标
2. 定义验收标准
3. 识别关键约束条件
4. 确定质量要求""",
    "clarify": """请对 Issue 进行需求澄清：

1. 澄清模糊需求
2. 补充遗漏细节
3. 确认优先级
4. 与现有系统一致性分析""",
    "plan": """请对 Issue 进行技术规划：

1. 提出技术方案
2. 评估方案优劣
3. 制定实施计划
4. 预估时间和资源""",
    "checklist": """请对技术规划进行质量检查：

1. 检查方案完整性
2. 验证代码规范符合度
3. 检查测试覆盖度
4. 验证文档完整性""",
    "tasks": """请将任务拆分为可执行的小任务：

1. 识别所有子任务
2. 确定任务依赖关系
3. 预估每个任务复杂度
4. 确定任务执行顺序""",
    "analyze": """请进行一致性分析：

1. 验证需求与方案一致性
2. 验证方案与任务拆分一致性
3. 检查依赖关系正确性
4. 识别潜在冲突""",
    "implement": """请执行编码实现任务：

1. 按照任务拆分顺序执行开发
2. 编写代码实现功能
3. 编写单元测试
4. 确保代码符合规范
5. 提交代码变更""",
    "submit": """请提交代码：

1. 确保所有更改已提交
2. 创建 PR（如果适用）
3. 列出所有变更""",
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
            EnvironmentStage(),     # 0: 环境准备（不需要审批）
            SpecifyStage(),         # 1: 规范定义
            ClarifyStage(),         # 2: 需求澄清
            PlanStage(),            # 3: 技术规划
            ChecklistStage(),       # 4: 质量检查
            TasksStage(),           # 5: 任务拆分
            AnalyzeStage(),         # 6: 一致性分析
            ImplementStage(),       # 7: 编码实现
            SubmitStage(),          # 8: 提交发布
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

    def get_stage(self, name: str):
        """获取指定名称的 Stage

        Args:
            name: Stage 名称

        Returns:
            Stage 对象，如果未找到返回 None
        """
        for stage in self._stages:
            if stage.name == name:
                return stage
        return None

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

            # 如果阶段需要审批且执行成功，设置等待审批状态
            if all_success and stage_obj.requires_approval:
                stage_obj.set_waiting_approval(task_result.message)
                self._status.state = PipelineState.RUNNING  # Pipeline 仍在运行，等待审批
            else:
                self._status.state = PipelineState.COMPLETED if all_success else PipelineState.FAILED
            self._status.reason = task_result.message

            # 更新 context
            if context_dict.get("workspace_path"):
                self._context.workspace_path = context_dict["workspace_path"]
            if context_dict.get("repo_name"):
                self._context.repo_name = context_dict["repo_name"]
            if context_dict.get("thread_id"):
                self._context.thread_id = context_dict["thread_id"]
            # 同步 SDD 阶段结果到 extra
            sdd_results = ["specify_result", "clarify_result", "plan_result",
                          "checklist_result", "tasks_result", "analyze_result",
                          "implement_result"]
            for key in sdd_results:
                if context_dict.get(key):
                    self._context.extra[key] = context_dict[key]

            return_result = {
                "success": all_success,
                "message": task_result.message,
                "stage_status": stage_obj.status,
            }
            # 返回 SDD 阶段结果
            for key in sdd_results:
                if context_dict.get(key):
                    return_result[key] = context_dict[key]
            return return_result

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
