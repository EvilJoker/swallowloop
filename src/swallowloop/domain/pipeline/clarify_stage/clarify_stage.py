"""Clarify Stage - 需求澄清阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class ClarifyTask(Task):
    """需求澄清任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="需求澄清",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行需求澄清"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        issue_description = context.get("issue_description", "")
        repo_url = context.get("repo_url", "")
        specify_result = context.get("specify_result", "")

        instruction = f"""请对 Issue 进行需求澄清：

# Issue 信息
标题: {issue_title}
描述: {issue_description}
仓库: {repo_url}

# 规范定义结果
{specify_result}

# 任务
1. 澄清模糊需求
2. 补充遗漏细节
3. 确认优先级
4. 与现有系统一致性分析

请以 JSON 格式返回结果：
{{
  "clarified_requirements": ["明确的需求1", "明确的需求2"],
  "missing_details": ["缺失细节1"],
  "priority_confirmed": "high|medium|low",
  "consistency_analysis": "一致性分析结果"
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "clarify",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"需求澄清失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="需求澄清完成",
                    data={"clarify_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="需求澄清完成（JSON解析失败）",
                    data={"clarify_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"需求澄清异常: {str(e)}")


class ClarifyStage(Stage):
    """需求澄清阶段"""

    def __init__(self):
        super().__init__(
            name="clarify",
            tasks=[ClarifyTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行需求澄清任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行需求澄清")
        logger.info("执行 Task: 需求澄清")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
