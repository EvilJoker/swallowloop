"""Specify Stage - 规范定义阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class SpecifyTask(Task):
    """规范定义任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="规范定义",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行规范定义"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        issue_description = context.get("issue_description", "")
        repo_url = context.get("repo_url", "")

        instruction = f"""请对 Issue 进行规范定义：

# Issue 信息
标题: {issue_title}
描述: {issue_description}
仓库: {repo_url}

# 任务
1. 明确需求范围和目标
2. 定义验收标准
3. 识别关键约束条件
4. 确定质量要求

请以 JSON 格式返回结果：
{{
  "requirements": ["需求1", "需求2"],
  "acceptance_criteria": ["标准1", "标准2"],
  "constraints": ["约束1"],
  "quality_requirements": ["质量要求1"]
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "specify",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"规范定义失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="规范定义完成",
                    data={"specify_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="规范定义完成（JSON解析失败）",
                    data={"specify_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"规范定义异常: {str(e)}")


class SpecifyStage(Stage):
    """规范定义阶段"""

    def __init__(self):
        super().__init__(
            name="specify",
            tasks=[SpecifyTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行规范定义任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行规范定义")
        logger.info("执行 Task: 规范定义")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
