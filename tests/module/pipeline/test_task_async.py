"""Task 异步 Handler 测试"""

import pytest
import asyncio
from swallowloop.domain.pipeline.task import Task, TaskResult


class TestTaskAsyncHandler:
    """Task 异步 Handler 测试"""

    def test_sync_handler(self):
        """同步 handler 正常工作"""
        def handler(ctx):
            ctx["sync"] = True
            return TaskResult(success=True, message="sync done")

        task = Task(name="sync_task", handler=handler)
        ctx, result = task.execute({})

        assert ctx["sync"] is True
        assert result.success is True

    @pytest.mark.asyncio
    async def test_async_handler(self):
        """异步 handler 正常工作"""
        async def handler(ctx):
            await asyncio.sleep(0.01)  # 模拟异步操作
            ctx["async"] = True
            return TaskResult(success=True, message="async done")

        task = Task(name="async_task", handler=handler)
        ctx, result = task.execute({})

        assert ctx["async"] is True
        assert result.success is True
        assert result.message == "async done"

    @pytest.mark.asyncio
    async def test_async_handler_with_error(self):
        """异步 handler 异常处理"""
        async def handler(ctx):
            raise ValueError("async error")

        task = Task(name="error_async_task", handler=handler)
        ctx, result = task.execute({})

        assert result.success is False
        assert "async error" in result.message

    def test_async_bound_method(self):
        """异步 bound method（类方法）"""
        class MyHandler:
            async def handle(self, ctx):
                ctx["bound_method"] = True
                return TaskResult(success=True, message="bound method done")

        handler_instance = MyHandler()
        task = Task(name="bound_task", handler=handler_instance.handle)
        ctx, result = task.execute({})

        assert ctx["bound_method"] is True
        assert result.success is True

    @pytest.mark.asyncio
    async def test_mixed_sync_async(self):
        """混合同步和异步 Task"""
        def sync_handler(ctx):
            ctx["step1"] = "sync"
            return TaskResult(success=True, message="sync done")

        async def async_handler(ctx):
            await asyncio.sleep(0.01)
            ctx["step2"] = "async"
            return TaskResult(success=True, message="async done")

        task1 = Task(name="sync", handler=sync_handler)
        task2 = Task(name="async", handler=async_handler)

        ctx1, result1 = task1.execute({})
        ctx2, result2 = task2.execute(ctx1)

        assert ctx2["step1"] == "sync"
        assert ctx2["step2"] == "async"
        assert result1.success is True
        assert result2.success is True

    def test_handler_returns_none(self):
        """handler 返回 None"""
        def handler(ctx):
            return None

        task = Task(name="none_task", handler=handler)
        ctx, result = task.execute({})

        assert result.success is False
        assert "未返回结果" in result.message

    def test_handler_raises_exception(self):
        """handler 抛出异常"""
        def handler(ctx):
            raise RuntimeError("handler error")

        task = Task(name="exception_task", handler=handler)
        ctx, result = task.execute({})

        assert result.success is False
        assert "handler error" in result.message

    def test_result_data_updates_context(self):
        """TaskResult.data 更新 context"""
        def handler(ctx):
            return TaskResult(success=True, message="done", data={"new_key": "new_value"})

        task = Task(name="data_task", handler=handler)
        ctx, result = task.execute({"old_key": "old_value"})

        assert ctx["old_key"] == "old_value"
        assert ctx["new_key"] == "new_value"
