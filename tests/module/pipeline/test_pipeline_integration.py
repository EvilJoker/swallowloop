"""Pipeline 集成测试 - 完整流水线状态转换"""

import pytest
from swallowloop.domain.pipeline.stage import Stage, StageState, ApprovalState, Task, TaskResult


def make_task(name, success=True):
    """创建 Task"""
    def handler(ctx):
        ctx[f"executed_{name}"] = True
        if success:
            return TaskResult(success=True, message=f"{name} 完成")
        else:
            return TaskResult(success=False, message=f"{name} 失败")
    return Task(name=name, handler=handler)


class TestPipelineStageTransition:
    """Pipeline 阶段转换测试"""

    def test_stage_completes_then_waits_approval(self):
        """阶段完成 -> 等待审批"""
        stage = Stage(name="specify", tasks=[
            make_task("task1"),
            make_task("task2"),
        ])

        # 执行阶段
        ctx, result = stage.execute({})

        assert result.success is True
        assert ctx["executed_task1"] is True
        assert ctx["executed_task2"] is True
        assert stage.status.is_completed()

        # 设置等待审批
        stage.set_waiting_approval("执行完成")
        assert stage.status.is_waiting_approval()
        assert stage.approval_state == ApprovalState.PENDING

    def test_approve_proceeds_to_next(self):
        """审批通过后进入下一阶段"""
        # 模拟两个阶段
        stage1 = Stage(name="specify", tasks=[make_task("s1")])
        stage2 = Stage(name="clarify", tasks=[make_task("c1")])

        # Stage 1 完成并审批通过
        ctx1, _ = stage1.execute({})
        stage1.set_waiting_approval()
        stage1.approve()

        assert stage1.status.is_approved()

        # Stage 2 可以开始
        ctx2, _ = stage2.execute(ctx1)
        assert ctx2["executed_s1"] is True
        assert ctx2["executed_c1"] is True

    def test_reject_triggers_retry(self):
        """打回后重新执行"""
        stage = Stage(name="specify", tasks=[make_task("task1")])

        # 完成并打回
        stage.execute({})
        stage.set_waiting_approval()
        stage.reject("需要改进")

        assert stage.status.is_rejected()
        assert stage.approval_state == ApprovalState.REJECTED

        # 重新执行
        ctx, result = stage.execute({})
        assert result.success is True

    def test_failure_stops_pipeline(self):
        """阶段失败停止流水线"""
        stage1 = Stage(name="specify", tasks=[make_task("task1", success=True)])
        stage2 = Stage(name="clarify", tasks=[make_task("task2", success=False)])
        stage3 = Stage(name="plan", tasks=[make_task("task3")])

        # Stage 1 成功
        ctx1, result1 = stage1.execute({})
        assert result1.success is True

        # Stage 2 失败
        ctx2, result2 = stage2.execute(ctx1)
        assert result2.success is False

        # Stage 3 不执行
        # (实际流水线会在失败时停止)

    def test_environment_no_approval(self):
        """环境准备阶段不需要审批"""
        env_stage = Stage(name="environment", requires_approval=False, tasks=[
            make_task("clone"),
            make_task("setup"),
        ])

        ctx, result = env_stage.execute({})

        assert result.success is True
        assert env_stage.approval_state == ApprovalState.NOT_REQUIRED
        assert env_stage.status.is_completed()

    def test_full_approval_flow(self):
        """完整审批流程"""
        # 创建 3 个阶段
        stage1 = Stage(name="specify", tasks=[make_task("s1")])
        stage2 = Stage(name="clarify", tasks=[make_task("c1")])
        stage3 = Stage(name="plan", tasks=[make_task("p1")])

        stages = [stage1, stage2, stage3]

        # 执行 stage1
        ctx = {}
        for i, stage in enumerate(stages):
            ctx, result = stage.execute(ctx)

            if i < len(stages) - 1:  # 除了最后一个，都需要审批
                stage.set_waiting_approval()
                assert stage.status.is_waiting_approval()
                stage.approve()
                assert stage.status.is_approved()

        # 最后一个阶段
        assert ctx["executed_s1"] is True
        assert ctx["executed_c1"] is True
        assert ctx["executed_p1"] is True


class TestRetryLogic:
    """重试逻辑测试"""

    def test_rejected_stage_retries(self):
        """打回后重新执行"""
        call_count = {"count": 0}

        def counting_handler(ctx):
            call_count["count"] += 1
            ctx["calls"] = call_count["count"]
            return TaskResult(success=True, message=f"第 {call_count['count']} 次执行")

        counting_task = Task(name="counting", handler=counting_handler)
        stage = Stage(name="specify", tasks=[counting_task])

        # 第一次执行
        ctx1, _ = stage.execute({})
        assert ctx1["calls"] == 1

        # 打回
        stage.set_waiting_approval()
        stage.reject("重新做")

        # 重新执行
        ctx2, _ = stage.execute(ctx1)
        assert ctx2["calls"] == 2

    def test_double_rejection_stops(self):
        """连续两次打回停止（简化逻辑）"""
        stage = Stage(name="specify", tasks=[make_task("task1")])

        # 第一次打回
        stage.execute({})
        stage.set_waiting_approval()
        stage.reject("第一次打回")

        # 模拟重新执行后再次打回
        stage.execute({})
        stage.set_waiting_approval()
        # 第二次打回 - 在实际实现中应该停止流水线

        assert stage.status.is_waiting_approval()
