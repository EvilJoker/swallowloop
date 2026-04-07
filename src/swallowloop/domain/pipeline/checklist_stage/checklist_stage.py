"""Checklist Stage - 质量检查阶段"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..stage import Stage, StageState, StageStatus, ApprovalState
from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class ChecklistTask(Task):
    """质量检查任务"""

    def __init__(self, agent=None):
        super().__init__(
            name="质量检查",
            handler=self._execute,
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent

    async def _execute(self, context: dict) -> TaskResult:
        """执行质量检查"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        issue_title = context.get("issue_title", "")
        plan_result = context.get("plan_result", "")

        instruction = f"""请对技术规划进行质量检查：

# Issue 信息
标题: {issue_title}

# 技术规划结果
{plan_result}

# 任务
1. 检查方案完整性
2. 验证代码规范符合度
3. 检查测试覆盖度
4. 验证文档完整性

请以 JSON 格式返回结果：
{{
  "completeness_check": {{
    "passed": true,
    "issues": ["问题1"]
  }},
  "code_standards_check": {{
    "passed": true,
    "issues": ["问题1"]
  }},
  "test_coverage_check": {{
    "passed": true,
    "coverage": "80%",
    "issues": []
  }},
  "documentation_check": {{
    "passed": true,
    "issues": []
  }},
  "overall_passed": true,
  "recommendations": ["建议1"]
}}"""

        agent_context = {
            "thread_id": context.get("thread_id", ""),
            "stage": "checklist",
        }

        try:
            result = await self._agent.execute(instruction, agent_context)
            if not result.success:
                return TaskResult(success=False, message=f"质量检查失败: {result.error}")

            import json
            try:
                data = json.loads(result.output)
                return TaskResult(
                    success=True,
                    message="质量检查完成",
                    data={"checklist_result": json.dumps(data, ensure_ascii=False)}
                )
            except json.JSONDecodeError:
                return TaskResult(
                    success=True,
                    message="质量检查完成（JSON解析失败）",
                    data={"checklist_result": result.output}
                )
        except Exception as e:
            return TaskResult(success=False, message=f"质量检查异常: {str(e)}")


class ChecklistStage(Stage):
    """质量检查阶段"""

    def __init__(self):
        super().__init__(
            name="checklist",
            tasks=[ChecklistTask()],
            requires_approval=True,
        )
        self._agent = None

    def set_agent(self, agent: "BaseAgent"):
        self._agent = agent
        if self.tasks:
            self.tasks[0].set_agent(agent)

    def execute(self, context: dict) -> tuple[dict, TaskResult]:
        """执行质量检查任务

        委托给 Task.execute() 处理，它会正确处理异步 handler
        """
        self._status = StageStatus(state=StageState.RUNNING, reason="执行质量检查")
        logger.info("执行 Task: 质量检查")

        task = self.tasks[0]
        context, result = task.execute(context)

        self._last_result = result
        self._status = StageStatus(
            state=StageState.COMPLETED if result.success else StageState.FAILED,
            reason=result.message
        )

        return context, result
