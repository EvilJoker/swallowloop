"""Issue API 集成测试"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil

from swallowloop.interfaces.web.api.issues import router, _issue_service, _executor_service, init_services
from swallowloop.application.service import IssueService, ExecutorService
from swallowloop.infrastructure.persistence import JsonIssueRepository


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def api_client(temp_data_dir):
    """创建测试客户端"""
    # 创建内存仓库代替全局服务
    from swallowloop.domain.repository import IssueRepository
    from tests.test_issue_service import MockExecutor

    class TestRepository(IssueRepository):
        def __init__(self):
            self._issues = {}

        def get(self, issue_id):
            from swallowloop.domain.model import IssueId
            return self._issues.get(str(issue_id))

        def save(self, issue):
            self._issues[str(issue.id)] = issue

        def list_all(self):
            return list(self._issues.values())

        def list_active(self):
            return [i for i in self._issues.values() if i.is_active]

        def delete(self, issue_id):
            from swallowloop.domain.model import IssueId
            key = str(issue_id)
            if key in self._issues:
                del self._issues[key]
                return True
            return False

    # 重新设置模块级别的全局变量
    import swallowloop.interfaces.web.api.issues as api_module
    repo = TestRepository()
    executor = MockExecutor()
    api_module._issue_service = IssueService(repo, executor)
    api_module._executor_service = None  # 不需要

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    return client


class TestIssueAPI:
    """Issue API 测试"""

    def test_list_issues_empty(self, api_client):
        """测试获取空列表"""
        response = api_client.get("/issues")
        assert response.status_code == 200
        assert response.json()["issues"] == []

    def test_create_issue(self, api_client):
        """测试创建 Issue"""
        response = api_client.post("/issues", json={"title": "测试", "description": "测试描述"})
        assert response.status_code == 201
        data = response.json()["issue"]
        assert data["title"] == "测试"
        assert data["description"] == "测试描述"
        assert data["status"] == "active"
        assert data["currentStage"] == "brainstorm"

    def test_get_issue(self, api_client):
        """测试获取单个 Issue"""
        # 先创建
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        # 再获取
        response = api_client.get(f"/issues/{issue_id}")
        assert response.status_code == 200
        assert response.json()["issue"]["title"] == "测试"

    def test_get_issue_not_found(self, api_client):
        """测试获取不存在的 Issue"""
        response = api_client.get("/issues/nonexistent")
        assert response.status_code == 404

    def test_update_issue_title(self, api_client):
        """测试更新 Issue 标题"""
        create_response = api_client.post("/issues", json={"title": "原始", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.patch(f"/issues/{issue_id}", json={"title": "新标题"})
        assert response.status_code == 200
        assert response.json()["issue"]["title"] == "新标题"

    def test_update_issue_archive(self, api_client):
        """测试归档 Issue"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.patch(f"/issues/{issue_id}", json={"status": "archived"})
        assert response.status_code == 200
        data = response.json()["issue"]
        assert data["status"] == "archived"
        assert data["archivedAt"] is not None

    def test_delete_issue(self, api_client):
        """测试删除 Issue"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.delete(f"/issues/{issue_id}")
        assert response.status_code == 200

        # 验证删除
        get_response = api_client.get(f"/issues/{issue_id}")
        assert get_response.status_code == 404

    def test_delete_issue_not_found(self, api_client):
        """测试删除不存在的 Issue"""
        response = api_client.delete("/issues/nonexistent")
        assert response.status_code == 404

    def test_approve_stage(self, api_client):
        """测试审批通过阶段"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.post(
            f"/issues/{issue_id}/stages/brainstorm/approve",
            json={"comment": "通过"}
        )
        assert response.status_code == 200
        data = response.json()["issue"]
        assert data["stages"]["brainstorm"]["status"] == "approved"
        # 应该进入下一阶段
        assert data["currentStage"] == "planFormed"

    def test_reject_stage(self, api_client):
        """测试打回阶段"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.post(
            f"/issues/{issue_id}/stages/brainstorm/reject",
            json={"reason": "方案不够详细"}
        )
        assert response.status_code == 200
        data = response.json()["issue"]
        assert data["stages"]["brainstorm"]["status"] == "rejected"
        # 检查评论
        comments = data["stages"]["brainstorm"]["comments"]
        assert len(comments) == 1
        assert comments[0]["action"] == "reject"
        assert comments[0]["content"] == "方案不够详细"

    def test_trigger_issue(self, api_client):
        """测试触发 AI 执行"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.post(
            f"/issues/{issue_id}/trigger",
            json={"stage": "brainstorm"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestIssueLifecycle:
    """Issue 完整生命周期测试"""

    def test_full_lifecycle(self, api_client):
        """测试从创建到归档的完整流程"""
        # 1. 创建 Issue
        response = api_client.post("/issues", json={
            "title": "新功能开发",
            "description": "开发一个很棒的功能"
        })
        assert response.status_code == 201
        issue_id = response.json()["issue"]["id"]

        # 2. 列出所有 Issue
        response = api_client.get("/issues")
        assert len(response.json()["issues"]) == 1

        # 3. 审批通过头脑风暴
        response = api_client.post(
            f"/issues/{issue_id}/stages/brainstorm/approve",
            json={"comment": "方案不错"}
        )
        assert response.status_code == 200
        assert response.json()["issue"]["currentStage"] == "planFormed"

        # 4. 审批通过方案成型
        response = api_client.post(
            f"/issues/{issue_id}/stages/planFormed/approve",
            json={"comment": "计划合理"}
        )
        assert response.status_code == 200
        assert response.json()["issue"]["currentStage"] == "detailedDesign"

        # 5. 打回详细设计
        response = api_client.post(
            f"/issues/{issue_id}/stages/detailedDesign/reject",
            json={"reason": "缺少错误处理"}
        )
        assert response.status_code == 200
        assert response.json()["issue"]["stages"]["detailedDesign"]["status"] == "rejected"

        # 6. 再次审批通过
        response = api_client.post(
            f"/issues/{issue_id}/stages/detailedDesign/approve",
            json={"comment": "已补充"}
        )
        assert response.status_code == 200

        # 7. 归档
        response = api_client.patch(f"/issues/{issue_id}", json={"status": "archived"})
        assert response.status_code == 200
        assert response.json()["issue"]["status"] == "archived"

        # 8. 删除
        response = api_client.delete(f"/issues/{issue_id}")
        assert response.status_code == 200
