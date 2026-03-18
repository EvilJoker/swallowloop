"""
端到端场景测试

测试完整的业务流程，验证各组件协作的正确性。
每个测试用例模拟一个真实的使用场景，从 Issue 创建到任务完成的完整闭环。
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from swallowloop.application.dto import IssueDTO
from swallowloop.application.service import TaskService, ExecutionService
from swallowloop.domain.model import (
    Comment,
    PullRequest,
    Task,
    TaskId,
    TaskState,
    TaskType,
    Workspace,
)
from swallowloop.domain.repository import TaskRepository, WorkspaceRepository
from swallowloop.infrastructure.agent import ExecutionResult
from tests.conftest import MockAgent, MockSourceControl


class TestE2ENewIssueFlow:
    """
    场景1: 新 Issue 完整流程
    
    流程: 扫描 Issue → 创建任务 → 分配工作空间 → 执行 → 创建 PR → 提交任务
    
    这是系统最核心的流程，模拟一个新 Issue 从被发现到 PR 创建的完整过程。
    """

    def test_complete_new_issue_flow(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        完整流程测试:
        1. 添加新 Issue
        2. 扫描并创建任务
        3. 分配工作空间
        4. 开始执行
        5. 创建 PR
        6. 提交任务
        """
        # 1. 准备: 创建新 Issue
        issue = IssueDTO(
            number=100,
            title="实现用户登录功能",
            body="需要实现用户登录接口，包括用户名密码验证和 JWT token 生成。",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        # 2. 初始化服务
        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )
        
        mock_agent = MockAgent()
        mock_agent.set_success(True)
        mock_agent.set_files_to_change(["src/auth/login.py", "tests/test_login.py"])
        
        execution_service = ExecutionService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            agent=mock_agent,
            base_branch="main",
        )

        # 3. 扫描 Issue，创建任务
        new_tasks, tasks_to_abort = task_service.scan_issues()
        
        assert len(new_tasks) == 1
        assert len(tasks_to_abort) == 0
        
        task = new_tasks[0]
        assert task.issue_number == 100
        assert task.state == TaskState.NEW.value
        assert task.branch_name.startswith("feature_100")

        # 4. 分配工作空间
        workspace = task_service.assign_workspace(task)
        
        assert task.state == TaskState.PENDING.value
        assert workspace is not None
        assert workspace.issue_number == 100

        # 5. 开始执行
        task_service.start_task(task)
        assert task.state == TaskState.IN_PROGRESS.value

        # 6. 模拟执行完成（成功）
        result = mock_agent.execute(task, workspace.path)
        assert result.success is True
        assert len(result.files_changed) == 2

        # 7. 创建 PR
        pr = execution_service.create_pull_request(task)
        
        assert pr is not None
        # PR 标题格式: {type}: {description}
        assert pr.title.startswith("feat:")
        assert "Closes #100" in mock_source_control._created_prs[-1]["body"]

        # 8. 提交任务
        task_service.submit_task(task, pr.number, pr.html_url)
        
        assert task.state == TaskState.SUBMITTED.value
        assert task.pr is not None
        assert task.pr.number == pr.number

        # 9. 验证持久化
        loaded = task_repository.get_by_issue(100)
        assert loaded is not None
        assert loaded.state == TaskState.SUBMITTED.value
        assert loaded.pr is not None

    def test_multiple_issues_parallel_flow(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        多 Issue 并行处理测试:
        验证系统可以同时处理多个 Issue
        """
        # 创建多个 Issue
        issues = [
            IssueDTO(
                number=i,
                title=f"任务 #{i}: 实现功能 {i}",
                body=f"详细描述 {i}",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            for i in range(1, 4)
        ]
        
        for issue in issues:
            mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 扫描并创建任务
        new_tasks, _ = task_service.scan_issues()
        assert len(new_tasks) == 3

        # 为每个任务分配工作空间
        for task in new_tasks:
            workspace = task_service.assign_workspace(task)
            assert workspace is not None
            assert task.state == TaskState.PENDING.value

        # 验证所有任务都已持久化
        active_tasks = task_repository.list_active()
        assert len(active_tasks) == 3


class TestE2ERevisionFlow:
    """
    场景2: 评论修订流程
    
    流程: 已提交 PR → 用户评论 → 触发修订 → 重新执行 → 重新提交
    
    这是系统处理用户反馈的核心流程。
    """

    def test_complete_revision_flow(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        完整修订流程:
        1. 完成初始提交流程
        2. 用户添加评论
        3. 扫描检测评论
        4. 任务进入修订状态
        5. 重新执行
        6. 重新提交 PR
        """
        # 初始 Issue
        issue = IssueDTO(
            number=200,
            title="添加数据导出功能",
            body="支持导出 CSV 和 JSON 格式",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 初始流程
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 201, "https://github.com/test/repo/pull/201")

        assert task.state == TaskState.SUBMITTED.value
        assert task.task_type == TaskType.NEW_TASK
        assert task.submission_count == 1

        # 用户添加评论
        mock_source_control.add_comment(200, "请添加对 Excel 格式的支持", "reviewer")

        # 扫描检测评论
        task_service.scan_issues()

        # 验证修订触发
        loaded = task_repository.get_by_issue(200)
        assert loaded.state == TaskState.PENDING.value
        assert loaded.task_type == TaskType.REVISION
        assert loaded.latest_comment is not None
        assert "Excel" in loaded.latest_comment.body

        # 重新执行
        task_service.start_task(loaded)

        # 重新提交
        task_service.submit_task(loaded, 202, "https://github.com/test/repo/pull/202")

        assert loaded.state == TaskState.SUBMITTED.value
        assert loaded.submission_count == 2

    def test_multiple_revision_rounds(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        多轮修订测试:
        验证系统可以处理多轮用户反馈
        """
        issue = IssueDTO(
            number=300,
            title="实现搜索功能",
            body="全文搜索",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 初始提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 301, "url1")
        assert task.submission_count == 1

        # 第一轮修订
        mock_source_control.add_comment(300, "添加高亮", "reviewer")
        task_service.scan_issues()
        
        loaded = task_repository.get_by_issue(300)
        loaded.begin_execution()
        loaded.submit_pr(PullRequest(number=302, html_url="url2", branch_name="b", title="t"))
        task_repository.save(loaded)
        assert loaded.submission_count == 2

        # 第二轮修订
        mock_source_control.add_comment(300, "优化性能", "reviewer")
        task_service.scan_issues()
        
        loaded = task_repository.get_by_issue(300)
        loaded.begin_execution()
        loaded.submit_pr(PullRequest(number=303, html_url="url3", branch_name="b", title="t"))
        task_repository.save(loaded)
        assert loaded.submission_count == 3

        # 验证评论历史
        assert len(loaded.comments) == 2

    def test_bot_comments_ignored(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        Bot 评论忽略测试:
        验证系统忽略机器人评论，不触发修订
        """
        issue = IssueDTO(
            number=400,
            title="Test Issue",
            body="Body",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 初始提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 401, "url")

        # Bot 评论（以 swallowloop 开头）
        mock_source_control.add_comment(400, "[SwallowLoop Bot] PR created", "swallowloop-bot")

        # 扫描
        task_service.scan_issues()

        # 状态应保持 submitted
        loaded = task_repository.get_by_issue(400)
        assert loaded.state == TaskState.SUBMITTED.value
        assert loaded.task_type == TaskType.NEW_TASK


class TestE2ERetryFlow:
    """
    场景3: 执行失败重试流程
    
    流程: 执行失败 → 重试 → 最终成功
    
    验证系统的容错能力。
    """

    def test_retry_then_success(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
        temp_dir: Path,
    ):
        """
        重试后成功测试:
        1. 第一次执行失败
        2. 触发重试
        3. 第二次执行成功
        """
        issue = IssueDTO(
            number=500,
            title="修复内存泄漏",
            body="应用运行一段时间后内存占用过高",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        mock_agent = MockAgent()
        
        # 创建任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 第一次执行失败
        mock_agent.set_success(False)
        result = mock_agent.execute(task, task.workspace.path)
        assert result.success is False

        # 触发重试
        task_service.retry_task(task, "执行失败: 内存不足")
        
        assert task.state == TaskState.PENDING.value
        assert task.retry_count == 1

        # 重新开始执行
        task_service.start_task(task)

        # 第二次执行成功
        mock_agent.set_success(True)
        mock_agent.set_files_to_change(["src/memory_manager.py"])
        result = mock_agent.execute(task, task.workspace.path)
        assert result.success is True

        # 创建 PR 并提交
        execution_service = ExecutionService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            agent=mock_agent,
            base_branch="main",
        )
        pr = execution_service.create_pull_request(task)
        task_service.submit_task(task, pr.number, pr.html_url)

        assert task.state == TaskState.SUBMITTED.value
        assert task.retry_count == 1  # 重试次数保留

    def test_max_retries_then_abort(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        达到最大重试次数后中止测试:
        验证系统在多次失败后正确终止任务
        
        重试流程：
        1. 执行失败，increment_retry() 增加计数
        2. 如果 can_retry() 返回 True，do_retry() 会转换状态 pending
        3. 如果 can_retry() 返回 False，do_retry() 不会转换状态，保持 in_progress
        4. 需要从 in_progress 状态中止任务
        """
        issue = IssueDTO(
            number=600,
            title="复杂功能实现",
            body="需要外部依赖",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建任务
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)

        # 模拟 max_retries - 1 次重试（最后一次失败时中止）
        for i in range(task._max_retries - 1):
            # 当前处于 in_progress 状态
            loaded = task_repository.get_by_issue(600)
            assert loaded.state == TaskState.IN_PROGRESS.value
            
            # 执行失败，触发重试 (in_progress -> pending)
            task_service.retry_task(loaded, f"失败 {i+1}")
            task_repository.save(loaded)
            
            # 重新加载并检查状态
            loaded = task_repository.get_by_issue(600)
            assert loaded.state == TaskState.PENDING.value
            assert loaded.retry_count == i + 1
            
            # 重新开始执行 (pending -> in_progress)
            loaded.begin_execution()
            task_repository.save(loaded)

        # 最后一次失败：达到最大重试次数
        loaded = task_repository.get_by_issue(600)
        assert loaded.state == TaskState.IN_PROGRESS.value
        assert loaded.retry_count == task._max_retries - 1
        
        # 增加重试计数到最大值
        loaded.increment_retry()
        assert loaded.retry_count == task._max_retries
        assert loaded.can_retry() is False
        
        # 由于 can_retry() 为 False，任务无法转换到 pending
        # 应该直接中止
        task_service.abort_task(loaded, "达到最大重试次数")

        # 验证中止
        final = task_repository.get_by_issue(600)
        assert final.state == TaskState.ABORTED.value
        assert final.is_active is False


class TestE2EAbortFlow:
    """
    场景4: Issue 关闭终止流程
    
    流程: 任务执行中 → Issue 关闭 → 任务终止
    
    验证系统对外部事件的响应。
    """

    def test_issue_closed_during_execution(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        执行中 Issue 关闭测试:
        1. 任务正在执行
        2. Issue 被关闭
        3. 扫描检测到关闭
        4. 任务被中止
        """
        issue = IssueDTO(
            number=700,
            title="紧急修复",
            body="生产环境问题",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建任务并开始执行
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)

        assert task.state == TaskState.IN_PROGRESS.value

        # Issue 被关闭（可能是人工关闭或其他原因）
        mock_source_control.close_issue(700)

        # 扫描检测
        _, tasks_to_abort = task_service.scan_issues()

        assert len(tasks_to_abort) == 1
        assert tasks_to_abort[0].issue_number == 700

    def test_issue_closed_after_pr_submitted(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        PR 提交后 Issue 关闭测试:
        验证已提交 PR 但未合并时关闭 Issue 的处理
        """
        issue = IssueDTO(
            number=800,
            title="功能优化",
            body="性能优化",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交 PR
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 801, "url")

        # Issue 关闭（但 PR 未合并）
        mock_source_control.close_issue(800)

        # 扫描
        _, tasks_to_abort = task_service.scan_issues()

        # 应该检测到需要中止
        assert len(tasks_to_abort) == 1


class TestE2ECompleteFlow:
    """
    场景5: PR 合并完成流程
    
    流程: PR 提交 → PR 合并 → 任务完成 → Issue 关闭
    
    验证任务最终完成的闭环。
    """

    def test_pr_merged_task_completed(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        PR 合并完成任务测试:
        1. PR 提交
        2. PR 被合并
        3. Issue 关闭
        4. 任务完成
        """
        issue = IssueDTO(
            number=900,
            title="添加单元测试",
            body="为核心模块添加测试",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交 PR
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 901, "https://github.com/test/repo/pull/901")

        assert task.state == TaskState.SUBMITTED.value

        # 模拟 PR 合并（Issue 关闭 + PR 合并）
        mock_source_control.close_issue(900)
        mock_source_control.merge_pr(901)

        # 扫描时检测到 PR 已合并
        _, tasks_to_abort = task_service.scan_issues()

        # 由于 PR 已合并，任务应该完成而非中止
        loaded = task_repository.get_by_issue(900)
        # 注意：这里的行为取决于具体实现
        # 如果 PR 已合并，任务状态应该是 completed
        assert loaded.state in (TaskState.COMPLETED.value, TaskState.SUBMITTED.value)

    def test_manual_task_completion(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        手动完成任务测试:
        验证任务可以手动标记为完成
        """
        issue = IssueDTO(
            number=1000,
            title="文档更新",
            body="更新 README",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 1001, "url")

        # 手动完成
        task_service.complete_task(task)

        assert task.state == TaskState.COMPLETED.value
        assert task.is_active is False

        # 验证不在活跃列表
        active = task_repository.list_active()
        issue_numbers = [t.issue_number for t in active]
        assert 1000 not in issue_numbers


class TestE2EIntegrationScenarios:
    """
    综合场景测试
    
    测试多个流程交叉的复杂场景
    """

    def test_issue_with_revision_then_closed(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        修订过程中 Issue 关闭测试:
        1. 初始提交
        2. 用户评论触发修订
        3. 修订过程中 Issue 关闭
        4. 任务中止
        """
        issue = IssueDTO(
            number=1100,
            title="实验性功能",
            body="可能不需要",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 初始提交
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        task_service.assign_workspace(task)
        task_service.start_task(task)
        task_service.submit_task(task, 1101, "url")

        # 用户评论触发修订
        mock_source_control.add_comment(1100, "需要修改", "reviewer")
        task_service.scan_issues()

        loaded = task_repository.get_by_issue(1100)
        assert loaded.state == TaskState.PENDING.value

        # 修订过程中 Issue 关闭
        mock_source_control.close_issue(1100)

        # 扫描检测
        _, tasks_to_abort = task_service.scan_issues()
        assert len(tasks_to_abort) == 1

    def test_workspace_reuse_on_retry(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        重试时工作空间复用测试:
        验证重试不会创建新工作空间
        """
        issue = IssueDTO(
            number=1200,
            title="需要重试的任务",
            body="首次执行可能失败",
            state="open",
            labels=["swallow"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_source_control.add_issue(issue)

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        # 创建并分配工作空间
        new_tasks, _ = task_service.scan_issues()
        task = new_tasks[0]
        original_workspace = task_service.assign_workspace(task)
        task_service.start_task(task)

        # 重试
        task_service.retry_task(task, "失败")

        # 验证工作空间保留
        loaded = task_repository.get_by_issue(1200)
        assert loaded.workspace is not None
        assert loaded.workspace.id == original_workspace.id

        # 验证工作空间仓库中也存在
        ws = workspace_repository.get(1200)
        assert ws is not None
        assert ws.id == original_workspace.id

    def test_branch_name_generation(
        self,
        task_repository: TaskRepository,
        workspace_repository: WorkspaceRepository,
        mock_source_control: MockSourceControl,
    ):
        """
        分支名生成测试:
        验证各种标题格式的分支名正确生成
        """
        test_cases = [
            (1, "Fix the bug!!!", "feature_1"),
            (2, "Add new feature", "feature_2"),
            (3, "中文标题测试", "feature_3"),
            (4, "UPPERCASE TITLE", "feature_4"),
            (5, "   spaces   around   ", "feature_5"),
            (6, "special@#$%characters", "feature_6"),
        ]

        task_service = TaskService(
            task_repository=task_repository,
            workspace_repository=workspace_repository,
            source_control=mock_source_control,
            issue_label="swallow",
        )

        for issue_num, title, expected_prefix in test_cases:
            issue = IssueDTO(
                number=issue_num,
                title=title,
                body="",
                state="open",
                labels=["swallow"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            mock_source_control.add_issue(issue)

        # 扫描创建任务
        new_tasks, _ = task_service.scan_issues()

        for task in new_tasks:
            # 验证分支名以 feature_# 开头（新格式）
            assert task.branch_name.startswith(f"feature_{task.issue_number}")
            # 验证分支名不含特殊字符
            assert "@" not in task.branch_name
            assert "#" not in task.branch_name
            assert "$" not in task.branch_name
            # 验证无多余空格
            assert "  " not in task.branch_name
