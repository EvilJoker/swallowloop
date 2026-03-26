"""Repository + JSON 持久化集成测试"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus
from swallowloop.infrastructure.persistence import JsonIssueRepository
from swallowloop.domain.statemachine import StageStateMachine


@pytest.fixture
def temp_dir():
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def repo(temp_dir):
    return JsonIssueRepository(project="test", data_dir=temp_dir)


class TestJsonPersistence:
    """JSON 持久化集成测试"""

    def test_save_and_retrieve(self, repo):
        """保存后能正确检索"""
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

    def test_persistence_after_reload(self, temp_dir):
        """重启后数据持久化"""
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

        # 模拟重启
        repo2 = JsonIssueRepository(project="persist-test", data_dir=temp_dir)
        retrieved = repo2.get(IssueId("persist-issue"))
        assert retrieved is not None
        assert retrieved.title == "持久化测试"

    def test_serialize_deserialize_stages(self, repo):
        """阶段序列化/反序列化"""
        issue = Issue(
            id=IssueId("stage-test"),
            title="阶段测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.EXECUTION,
            created_at=datetime.now(),
        )

        machine = StageStateMachine(issue, repo)

        # 批准多个阶段
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.approve(Stage.BRAINSTORM, "通过")
        machine.advance(Stage.BRAINSTORM)

        machine.start(Stage.PLAN_FORMED)
        machine.execute(Stage.PLAN_FORMED)
        machine.approve(Stage.PLAN_FORMED, "通过")
        machine.advance(Stage.PLAN_FORMED)

        machine.start(Stage.DETAILED_DESIGN)
        machine.execute(Stage.DETAILED_DESIGN)
        machine.approve(Stage.DETAILED_DESIGN, "通过")
        machine.advance(Stage.DETAILED_DESIGN)

        machine.start(Stage.TASK_SPLIT)
        machine.execute(Stage.TASK_SPLIT)
        machine.approve(Stage.TASK_SPLIT, "通过")
        machine.advance(Stage.TASK_SPLIT)

        machine.start(Stage.EXECUTION)

        repo.save(issue)
        retrieved = repo.get(IssueId("stage-test"))

        assert retrieved.stages[Stage.BRAINSTORM].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.PLAN_FORMED].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.DETAILED_DESIGN].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.TASK_SPLIT].status == StageStatus.APPROVED
        assert retrieved.stages[Stage.EXECUTION].status == StageStatus.RUNNING

    def test_serialize_deserialize_comments(self, repo):
        """评论序列化/反序列化"""
        issue = Issue(
            id=IssueId("comment-test"),
            title="评论测试",
            description="",
            status=IssueStatus.ACTIVE,
            current_stage=Stage.BRAINSTORM,
            created_at=datetime.now(),
        )

        machine = StageStateMachine(issue, repo)
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.reject(Stage.BRAINSTORM, "方案不够详细")
        machine.start(Stage.BRAINSTORM)
        machine.execute(Stage.BRAINSTORM)
        machine.approve(Stage.BRAINSTORM, "已补充")

        repo.save(issue)
        retrieved = repo.get(IssueId("comment-test"))

        comments = retrieved.stages[Stage.BRAINSTORM].comments
        assert len(comments) == 2
        assert comments[0].action == "reject"
        assert comments[0].content == "方案不够详细"
        assert comments[1].action == "approve"
        assert comments[1].content == "已补充"
