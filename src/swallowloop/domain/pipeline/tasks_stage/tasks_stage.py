"""Tasks Stage - 任务拆分阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class TasksTask(Task):
    """任务拆分任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="任务拆分",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行任务拆分"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        plan_result = context.get("plan_result", "")

        instruction = f"""请将任务拆分为可执行的小任务：

# Issue 信息
标题: {issue_title}

# 技术规划结果
{plan_result}

# 任务
1. 识别所有子任务
2. 确定任务依赖关系
3. 预估每个任务复杂度
4. 确定任务执行顺序

请以 JSON 格式返回结果：
{{
  "tasks": [
    {{
      "id": 1,
      "name": "任务名称",
      "description": "任务描述",
      "complexity": "low|medium|high",
      "estimated_time": "时间预估",
      "dependencies": []
    }}
  ],
  "execution_order": [1, 2, 3],
  "total_estimated_time": "总时间预估"
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "tasks",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"任务拆分失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="任务拆分完成",
                    data={"tasks_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="任务拆分完成（JSON解析失败）",
                    data={"tasks_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"任务拆分异常: {str(e)}")


class TasksStage(Stage):
    """任务拆分阶段"""

    def __init__(self):
        super().__init__(
            name="tasks",
            tasks=[TasksTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行任务拆分任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行任务拆分")
        logger.info("执行 Task: 任务拆分")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
