"""头脑风暴任务 - 调用 agent.execute() 执行结构化头脑风暴"""

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....infrastructure.agent import BaseAgent

from ..task import Task, TaskResult

logger = logging.getLogger(__name__)


class BrainstormTask(Task):
    """头脑风暴任务 - 调用 agent.execute() 执行结构化头脑风暴"""

    def __init__(self, agent=None):
        super().__init__(
            name="执行头脑风暴",
            handler=self._execute_async,
            description="调用 DeerFlow Agent 进行结构化头脑风暴"
        )
        self._agent = agent

    def set_agent(self, agent: "BaseAgent"):
        """注入 Agent"""
        self._agent = agent

    async def _execute_async(self, context: dict) -> TaskResult:
        """异步执行头脑风暴"""
        if not self._agent:
            return TaskResult(success=False, message="Agent 未配置")

        # 构建 task_message
        issue_title = context.get("issue_title", "")
        issue_description = context.get("issue_description", "")
        repo_url = context.get("repo_url", "")
        thread_id = context.get("thread_id", "")

        instruction = f"""请对以下 Issue 进行头脑风暴，直接输出 JSON 格式结果，不要输出任何其他内容。

输入信息：
- Issue 标题：{issue_title}
- Issue 描述：{issue_description}
- 代码仓库：{repo_url}

输出格式（严格遵循，仅输出 JSON，不要有其他文字）：
{{
  "solutions": [
    {{
      "id": 1,
      "name": "方案名称",
      "description": "方案描述（100字内）",
      "pros": ["优点1", "优点2"],
      "cons": ["缺点1"],
      "complexity": "low|medium|high"
    }}
  ],
  "analysis": "问题分析（50字内）",
  "recommendation": {{
    "selected_id": 1,
    "reason": "推荐理由（50字内）"
  }}
}}

要求：
- 至少提出 3 个方案
- complexity 表示实现复杂度
- 仅输出 JSON，不要有任何解释、思考过程或额外文字"""

        workspace_path = context.get("workspace_path", "")
        # DeerFlow 使用 result.json 轮询结果
        result_file = f"{workspace_path}/result.json" if workspace_path else ""
        stage_file = f"{workspace_path}/brief.md" if workspace_path else ""

        task_message = instruction
        agent_context = {
            "thread_id": thread_id,
            "stage": "brainstorm",
            "stage_file": stage_file,
            "result_file": result_file,
        }

        # 调用异步 agent.execute()
        result = await self._agent.execute(task_message, agent_context)

        if not result.success:
            return TaskResult(success=False, message=f"头脑风暴失败: {result.error}")

        # 解析 JSON
        try:
            data = json.loads(result.output)
            logger.info(f"头脑风暴完成，生成了 {len(data.get('solutions', []))} 个方案")
            return TaskResult(
                success=True,
                message="头脑风暴完成",
                data={"brainstorm_result": json.dumps(data, ensure_ascii=False)}
            )
        except json.JSONDecodeError as e:
            # JSON 解析失败，存入原始文本
            logger.warning(f"头脑风暴 JSON 解析失败，降级为原始文本: {e}")
            return TaskResult(
                success=True,
                message=f"头脑风暴完成（JSON解析失败）",
                data={"brainstorm_result": result.output}
            )
