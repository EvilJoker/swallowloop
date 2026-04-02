"""Pipeline 模块测试"""

import pytest
from swallowloop.domain.pipeline import (
    Pipeline,
    Stage,
    Task,
    TaskResult,
    PipelineResult,
)


class TestTaskResult:
    """TaskResult 测试"""

    def test_create_success_result(self):
        """创建成功结果"""
        result = TaskResult(success=True, message="成功")
        assert result.success is True
        assert result.message == "成功"
        assert result.data == {}

    def test_create_failure_result(self):
        """创建失败结果"""
        result = TaskResult(success=False, message="失败", data={"error": "详情"})
        assert result.success is False
        assert result.message == "失败"
        assert result.data == {"error": "详情"}

    def test_default_data(self):
        """默认 data 为空字典"""
        result = TaskResult(success=True, message="测试")
        assert result.data == {}


class TestTask:
    """Task 测试"""

    def test_task_execute_success(self):
        """Task 执行成功"""
        def handler(ctx):
            ctx["step1"] = "done"
            return TaskResult(success=True, message="完成")

        task = Task(name="测试任务", handler=handler)
        ctx, result = task.execute({})

        assert ctx["step1"] == "done"
        assert result.success is True
        assert result.message == "完成"

    def test_task_execute_failure(self):
        """Task 执行失败"""
        def handler(ctx):
            return TaskResult(success=False, message="执行失败")

        task = Task(name="失败任务", handler=handler)
        ctx, result = task.execute({"key": "value"})

        assert ctx["key"] == "value"  # context 不变
        assert result.success is False
        assert result.message == "执行失败"

    def test_task_execute_returns_none(self):
        """Task 返回 None"""
        def handler(ctx):
            return None

        task = Task(name="空任务", handler=handler)
        ctx, result = task.execute({})

        assert result.success is False
        assert result.message == "Task 未返回结果"

    def test_task_execute_returns_nothing(self):
        """Task 不返回"""
        def handler(ctx):
            pass

        task = Task(name="无返回任务", handler=handler)
        ctx, result = task.execute({})

        assert result.success is False
        assert result.message == "Task 未返回结果"


class TestStage:
    """Stage 测试"""

    def test_stage_execute_all_success(self):
        """Stage 内所有 Task 都成功"""
        def make_task(name):
            def handler(ctx):
                ctx[name] = True
                return TaskResult(success=True, message=f"{name} 完成")
            return Task(name=name, handler=handler)

        stage = Stage(name="测试阶段", tasks=[make_task("t1"), make_task("t2")])
        ctx, result = stage.execute({})

        assert ctx["t1"] is True
        assert ctx["t2"] is True
        assert result.success is True
        assert "测试阶段" in result.message

    def test_stage_execute_stops_on_failure(self):
        """Stage 内 Task 失败时停止"""
        def make_task(name, should_fail=False):
            def handler(ctx):
                ctx[name] = True
                if should_fail:
                    return TaskResult(success=False, message=f"{name} 失败")
                return TaskResult(success=True, message=f"{name} 完成")
            return Task(name=name, handler=handler)

        stage = Stage(
            name="失败阶段",
            tasks=[make_task("t1"), make_task("t2", should_fail=True), make_task("t3")]
        )
        ctx, result = stage.execute({})

        assert ctx["t1"] is True
        assert ctx["t2"] is True
        assert "t3" not in ctx  # 第三个 Task 未执行
        assert result.success is False
        assert result.message == "t2 失败"

    def test_stage_add_task(self):
        """动态添加 Task"""
        stage = Stage(name="空阶段", tasks=[])
        stage.add_task(Task(name="task1", handler=lambda ctx: (ctx, TaskResult(success=True, message="ok"))[1] if False else (ctx.__setitem__('a', 1), TaskResult(success=True, message="ok"))[1]))

        assert len(stage.tasks) == 1


class TestPipeline:
    """Pipeline 测试"""

    def test_pipeline_execute_all_success(self):
        """Pipeline 所有 Stage 都成功"""
        def make_task(name):
            def handler(ctx):
                ctx[name] = True
                return TaskResult(success=True, message=f"{name} 完成")
            return Task(name=name, handler=handler)

        def make_stage(name, task_names):
            return Stage(name=name, tasks=[make_task(n) for n in task_names])

        pipeline = Pipeline(
            name="成功流水线",
            stages=[
                make_stage("阶段1", ["s1_t1", "s1_t2"]),
                make_stage("阶段2", ["s2_t1"]),
            ]
        )

        ctx, result = pipeline.execute({})

        assert ctx["s1_t1"] is True
        assert ctx["s1_t2"] is True
        assert ctx["s2_t1"] is True
        assert result.success is True
        assert result.message == "Pipeline 执行完成"
        assert result.failed_stage is None
        assert result.failed_task is None

    def test_pipeline_stops_on_stage_failure(self):
        """Pipeline 在 Stage 失败时停止"""
        def success_task(name):
            def handler(ctx):
                ctx[name] = True
                return TaskResult(success=True, message=f"{name} 完成")
            return Task(name=name, handler=handler)

        def fail_task(name):
            def handler(ctx):
                ctx[name] = True
                return TaskResult(success=False, message=f"{name} 失败")
            return Task(name=name, handler=handler)

        s1 = Stage(name="成功阶段", tasks=[success_task("t1")])
        s2 = Stage(name="失败阶段", tasks=[fail_task("t2"), success_task("t3")])
        s3 = Stage(name="未执行阶段", tasks=[success_task("t4")])

        pipeline = Pipeline(name="失败流水线", stages=[s1, s2, s3])
        ctx, result = pipeline.execute({})

        assert ctx["t1"] is True
        assert "t2" in ctx  # t2 执行了但失败
        assert "t3" not in ctx  # t3 未执行
        assert "t4" not in ctx  # s3 未执行

        assert result.success is False
        assert "失败阶段" in result.message
        assert result.failed_stage == "失败阶段"
        assert result.failed_task == "t2 失败"

    def test_pipeline_progress(self):
        """Pipeline 进度追踪"""
        pipeline = Pipeline(name="测试", stages=[
            Stage(name="s1", tasks=[]),
            Stage(name="s2", tasks=[]),
            Stage(name="s3", tasks=[]),
        ])

        # 初始状态
        assert pipeline.current_stage_index() == 0
        assert pipeline.current_stage().name == "s1"
        assert pipeline.is_done() is False

    def test_pipeline_is_done(self):
        """Pipeline 完成判断"""
        def done_stage(name):
            def handler(ctx):
                return TaskResult(success=True, message="完成")
            return Stage(name=name, tasks=[Task(name="t", handler=handler)])

        pipeline = Pipeline(name="测试", stages=[done_stage("s1"), done_stage("s2")])
        ctx, result = pipeline.execute({})

        assert pipeline.is_done() is True
        assert result.success is True


class TestPipelineIntegration:
    """Pipeline 集成测试"""

    def test_sequential_context_passing(self):
        """验证 context 在 Task 间传递"""
        def task_add(key, value):
            def handler(ctx):
                ctx[key] = value
                return TaskResult(success=True, message="ok")
            return Task(name=f"add_{key}", handler=handler)

        stage = Stage(name="累加阶段", tasks=[
            task_add("step1", 1),
            task_add("step2", 2),
            task_add("step3", 3),
        ])

        ctx, result = stage.execute({})
        assert ctx["step1"] == 1
        assert ctx["step2"] == 2
        assert ctx["step3"] == 3

    def test_empty_pipeline(self):
        """空 Pipeline"""
        pipeline = Pipeline(name="空流水线", stages=[])
        ctx, result = pipeline.execute({"key": "value"})

        assert ctx == {"key": "value"}
        assert result.success is True

    def test_single_task_pipeline(self):
        """单 Task Pipeline"""
        task = Task(name="唯一任务", handler=lambda ctx: (ctx.update({"done": True}), TaskResult(success=True, message="完成"))[1])
        stage = Stage(name="单阶段", tasks=[task])
        pipeline = Pipeline(name="单任务流水线", stages=[stage])

        ctx, result = pipeline.execute({})
        assert ctx["done"] is True
        assert result.success is True
