"""Implement Stage - 编码实现阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class ImplementTask(Task):
    """编码实现任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="编码实现",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行编码实现"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        issue_description = context.get("issue_description", "")
        repo_url = context.get("repo_url", "")
        tasks_result = context.get("tasks_result", "")

        instruction = f"""请执行编码实现任务：

# Issue 信息
标题: {issue_title}
描述: {issue_description}
仓库: {repo_url}

# 任务拆分结果
{tasks_result}

# 任务
1. 按照任务拆分顺序执行开发
2. 编写代码实现功能
3. 编写单元测试
4. 确保代码符合规范
5. 提交代码变更

请以 JSON 格式返回结果：
{{
  "completed_tasks": [
    {{
      "task_id": 1,
      "task_name": "任务名称",
      "status": "completed",
      "code_changes": ["文件1", "文件2"],
      "test_added": ["测试文件1"]
    }}
  ],
  "pending_tasks": [],
  "code_quality": "good|needs_improvement",
  "issues_encountered": [],
  "commit_sha": "commit hash"
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "implement",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"编码实现失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="编码实现完成",
                    data={"implement_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="编码实现完成（JSON解析失败）",
                    data={"implement_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"编码实现异常: {str(e)}")


class ImplementStage(Stage):
    """编码实现阶段"""

    def __init__(self):
        super().__init__(
            name="implement",
            tasks=[ImplementTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行编码实现任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行编码实现")
        logger.info("执行 Task: 编码实现")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
