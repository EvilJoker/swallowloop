"""Plan Stage - 技术规划阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class PlanTask(Task):
    """技术规划任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="技术规划",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行技术规划"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        issue_description = context.get("issue_description", "")
        repo_url = context.get("repo_url", "")
        clarify_result = context.get("clarify_result", "")

        instruction = f"""请对 Issue 进行技术规划：

# Issue 信息
标题: {issue_title}
描述: {issue_description}
仓库: {repo_url}

# 需求澄清结果
{clarify_result}

# 任务
1. 提出技术方案
2. 评估方案优劣
3. 制定实施计划
4. 预估时间和资源

请以 JSON 格式返回结果：
{{
  "solutions": [
    {{
      "name": "方案名称",
      "description": "方案描述",
      "pros": ["优点1", "优点2"],
      "cons": ["缺点1"],
      "complexity": "low|medium|high",
      "estimated_time": "时间预估"
    }}
  ],
  "recommended_solution": 1,
  "implementation_plan": ["步骤1", "步骤2"],
  "risk_assessment": "风险评估"
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "plan",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"技术规划失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="技术规划完成",
                    data={"plan_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="技术规划完成（JSON解析失败）",
                    data={"plan_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"技术规划异常: {str(e)}")


class PlanStage(Stage):
    """技术规划阶段"""

    def __init__(self):
        super().__init__(
            name="plan",
            tasks=[PlanTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行技术规划任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行技术规划")
        logger.info("执行 Task: 技术规划")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
