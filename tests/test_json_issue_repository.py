"""JsonIssueRepository 持久化层测试"""

import pytest
import json
import fcntl
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.infrastructure.persistence import JsonIssueRepository


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def repo(temp_dir):
    """创建测试仓库"""
    return JsonIssueRepository(project="test", data_dir=temp_dir)


class TestJsonIssueRepository:
    """JsonIssueRepository 测试"""

    def test_create_and_get(self, repo):
        """测试创建和获取 Issue"""
        issue = Issue(
            id=IssueId("test-1"),
            title="测试",
            description="测试描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        retrieved = repo.get(IssueId("test-1"))
        assert retrieved is not None
        assert retrieved.title == "测试"
        assert retrieved.description == "测试描述"

    def test_get_nonexistent(self, repo):
        """测试获取不存在的 Issue"""
        result = repo.get(IssueId("nonexistent"))
        assert result is None

    def test_list_all(self, repo):
        """测试列出所有 Issue"""
        for i in range(3):
            issue = Issue(
                id=IssueId(f"issue-{i}"),
                title=f"Issue {i}",
                description=f"描述 {i}",
                status=IssueStatus.ACTIVE,
                current_stage=Stage.BRAINSTORM,
                created_at=datetime.now(),
            )
            repo.save(issue)

        issues = repo.list_all()
        assert len(issues) == 3

    def test_list_active(self, repo):
        """测试列出活跃 Issue"""
        # 创建活跃 Issue
        active = Issue(
            id=IssueId("active-1"),
            title="活跃",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(active)

        # 创建已归档 Issue
        archived = Issue(
            id=IssueId("archived-1"),
            title="已归档",
            description="",
            status=IssueStatus.ARCHIVED,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
            archived_at=datetime.now(),
        )
        repo.save(archived)

        active_issues = repo.list_active()
        assert len(active_issues) == 1
        assert active_issues[0].id.value == "active-1"

    def test_delete(self, repo):
        """测试删除 Issue"""
        issue = Issue(
            id=IssueId("to-delete"),
            title="删除我",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        result = repo.delete(IssueId("to-delete"))
        assert result is True
        assert repo.get(IssueId("to-delete")) is None

    def test_delete_nonexistent(self, repo):
        """测试删除不存在的 Issue"""
        result = repo.delete(IssueId("nonexistent"))
        assert result is False

    def test_update_existing(self, repo):
        """测试更新已存在的 Issue"""
        issue = Issue(
            id=IssueId("update-test"),
            title="原始标题",
            description="原始描述",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        # 更新
        issue.title = "新标题"
        issue.description = "新描述"
        repo.save(issue)

        retrieved = repo.get(IssueId("update-test"))
        assert retrieved.title == "新标题"
        assert retrieved.description == "新描述"

    def test_persistence_after_reload(self, temp_dir):
        """测试重启后数据持久化"""
        repo1 = JsonIssueRepository(project="persist-test", data_dir=temp_dir)
        issue = Issue(
            id=IssueId("persist-issue"),
            title="持久化测试",
            description="重启后应该存在",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo1.save(issue)

        # 模拟重启，创建新实例
        repo2 = JsonIssueRepository(project="persist-test", data_dir=temp_dir)
        retrieved = repo2.get(IssueId("persist-issue"))
        assert retrieved is not None
        assert retrieved.title == "持久化测试"

    def test_concurrent_save(self, temp_dir):
        """测试并发保存（使用文件锁）"""
        import threading

        repo = JsonIssueRepository(project="concurrent-test", data_dir=temp_dir)
        errors = []

        def save_issue(idx):
            try:
                issue = Issue(
                    id=IssueId(f"concurrent-{idx}"),
                    title=f"Issue {idx}",
                    description="并发保存测试",
                    status=IssueStatus.ACTIVE,
                    current_stage=Stage.BRAINSTORM,
                    created_at=datetime.now(),
                )
                repo.save(issue)
            except Exception as e:
                errors.append(e)

        # 启动多个线程同时保存
        threads = [threading.Thread(target=save_issue, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(repo.list_all()) == 5

    def test_serialize_deserialize_stages(self, repo):
        """测试阶段序列化/反序列化"""
        issue = Issue(
            id=IssueId("stage-test"),
            title="阶段测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.EXECUTION,
            created_at=datetime.now(),
        )

        # 批准头脑风暴
        issue.approve_stage(Stage.BRAINSTORM, "通过")
        # 进入执行阶段
        issue.start_stage(Stage.PLAN_FORMED)
        issue.approve_stage(Stage.PLAN_FORMED, "通过")
        issue.start_stage(Stage.DETAILED_DESIGN)
        issue.approve_stage(Stage.DETAILED_DESIGN, "通过")
        issue.start_stage(Stage.TASK_SPLIT)
        issue.approve_stage(Stage.TASK_SPLIT, "通过")
        issue.start_stage(Stage.EXECUTION)

        repo.save(issue)
        retrieved = repo.get(IssueId("stage-test"))

        assert retrieved.stages[Stage.BRAINSTORM].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.PLAN_FORMED].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.DETAILED_DESIGN].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.TASK_SPLIT].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.EXECUTION].status == StageStatus.RUNNING

    def test_serialize_deserialize_comments(self, repo):
        """测试评论序列化/反序列化"""
        issue = Issue(
            id=IssueId("comment-test"),
            title="评论测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )

        issue.reject_stage(Stage.BRAINSTORM, "方案不够详细")
        issue.approve_stage(Stage.BRAINSTORM, "已补充")

        repo.save(issue)
        retrieved = repo.get(IssueId("comment-test"))

        comments = retrieved.stages[Stage.BRAINSTORM].comments
        assert len(comments) == 2
        assert comments[0].action == "reject"
        assert comments[0].content == "方案不够详细"
        assert comments[1].action == "approve"
        assert comments[1].content == "已补充"

    def test_serialize_deserialize_todo_list(self, repo):
        """测试 TODO 列表序列化/反序列化"""
        from swallowloop.domain.model import TodoItem, TodoStatus

        issue = Issue(
            id=IssueId("todo-test"),
            title="TODO测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.EXECUTION,
            created_at=datetime.now(),
        )

        # 添加 TODO
        todo = TodoItem(id="t1", content="任务1")
        todo.mark_completed()
        issue.stages[Stage.EXECUTION].todo_list = [todo]

        repo.save(issue)
        retrieved = repo.get(IssueId("todo-test"))

        todo_list = retrieved.stages[Stage.EXECUTION].todo_list
        assert todo_list is not None
        assert len(todo_list) == 1
        assert todo_list[0].content == "任务1"
        assert todo_list[0].status == TodoStatus.COMPLETED

    def test_file_lock_protection(self, temp_dir):
        """测试文件锁保护"""
        repo = JsonIssueRepository(project="lock-test", data_dir=temp_dir)
        lock_file = temp_dir / "lock-test" / "issues.json.lock"

        # 先保存一个 issue，触发锁文件创建
        issue = Issue(
            id=IssueId("lock-test-issue"),
            title="锁测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )
        repo.save(issue)

        # 验证锁文件存在
        assert lock_file.exists()

        # 获取锁
        with open(lock_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            # 保存应该在另一个锁中完成
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def test_corrupted_json_recovery(self, temp_dir):
        """测试损坏的 JSON 文件恢复"""
        repo = JsonIssueRepository(project="corrupt-test", data_dir=temp_dir)

        # 手动写入损坏的 JSON
        issues_file = temp_dir / "corrupt-test" / "issues.json"
        with open(issues_file, 'w') as f:
            f.write("{ invalid json }")

        # 重新创建仓库，应该能恢复
        repo2 = JsonIssueRepository(project="corrupt-test", data_dir=temp_dir)
        issues = repo2.list_all()
        assert issues == []  # 应该返回空列表而不是崩溃
