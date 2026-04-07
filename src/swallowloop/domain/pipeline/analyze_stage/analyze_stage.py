"""Analyze Stage - 一致性分析阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class AnalyzeTask(Task):
    """一致性分析任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="一致性分析",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行一致性分析"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        tasks_result = context.get("tasks_result", "")

        instruction = f"""请进行一致性分析：

# Issue 信息
标题: {issue_title}

# 任务拆分结果
{tasks_result}

# 任务
1. 验证需求与方案一致性
2. 验证方案与任务拆分一致性
3. 检查依赖关系正确性
4. 识别潜在冲突

请以 JSON 格式返回结果：
{{
  "requirements_consistency": {{
    "passed": true,
    "issues": []
  }},
  "solution_consistency": {{
    "passed": true,
    "issues": []
  }},
  "dependency_analysis": {{
    "passed": true,
    "issues": []
  }},
  "conflict_detection": {{
    "passed": true,
    "conflicts": []
  }},
  "overall_passed": true,
  "recommendations": []
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "analyze",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"一致性分析失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="一致性分析完成",
                    data={"analyze_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="一致性分析完成（JSON解析失败）",
                    data={"analyze_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"一致性分析异常: {str(e)}")


class AnalyzeStage(Stage):
    """一致性分析阶段"""

    def __init__(self):
        super().__init__(
            name="analyze",
            tasks=[AnalyzeTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行一致性分析任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行一致性分析")
        logger.info("执行 Task: 一致性分析")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
