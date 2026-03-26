"""API + Service 集成测试"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from swallowloop.interfaces.web.api.issues import router
from swallowloop.application.service import IssueService
from swallowloop.infrastructure.persistence import InMemoryIssueRepository
from tests.helpers import MockExecutor


@pytest.fixture
def api_client():
    """创建测试客户端"""
    from swallowloop.domain.repository import IssueRepository

    class TestRepository(IssueRepository):
        def __init__(self):
            self._issues = {}

        def get(self, issue_id):
            return self._issues.get(str(issue_id))

        def save(self, issue):
            self._issues[str(issue.id)] = issue

        def list_all(self):
            return list(self._issues.values())

        def list_active(self):
            return [i for i in self._issues.values() if i.is_active]

        def delete(self, issue_id):
            key = str(issue_id)
            if key in self._issues:
                del self._issues[key]
                return True
            return False

        def list_stages_by_status(self, status):
            from swallowloop.domain.model import Stage
            result = []
            for issue in self.list_active():
                for stage, state in issue.stages.items():
                    if state.status == status:
                        result.append((issue, stage))
            return result

    import swallowloop.interfaces.web.api.issues as api_module
    repo = TestRepository()
    executor = MockExecutor(repository=repo)
    api_module._issue_service = IssueService(repo, executor)
    api_module._executor_service = None

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestAPIWithService:
    """API 与 Service 集成测试"""

    def test_list_issues_empty(self, api_client):
        """获取空列表"""
        response = api_client.get("/issues")
        assert response.status_code == 200
        assert response.json()["issues"] == []

    def test_create_issue(self, api_client):
        """创建 Issue"""
        response = api_client.post("/issues", json={"title": "测试", "description": "测试描述"})
        assert response.status_code == 201
        data = response.json()["issue"]
        assert data["title"] == "测试"
        assert data["currentStage"] == "brainstorm"

    def test_get_issue(self, api_client):
        """获取单个 Issue"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.get(f"/issues/{issue_id}")
        assert response.status_code == 200
        assert response.json()["issue"]["title"] == "测试"

    def test_update_issue(self, api_client):
        """更新 Issue"""
        create_response = api_client.post("/issues", json={"title": "原始", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        response = api_client.patch(f"/issues/{issue_id}", json={"title": "新标题"})
        assert response.status_code == 200
        assert response.json()["issue"]["title"] == "新标题"

    def test_approve_stage_workflow(self, api_client):
        """审批通过流程"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        # 触发 AI 执行
        api_client.post(f"/issues/{issue_id}/trigger", json={"stage": "brainstorm"})

        # 审批通过
        response = api_client.post(
            f"/issues/{issue_id}/stages/brainstorm/approve",
            json={"comment": "通过"}
        )
        assert response.status_code == 200
        data = response.json()["issue"]
        assert data["stages"]["brainstorm"]["status"] == "approved"
        assert data["currentStage"] == "planFormed"

    def test_reject_stage_workflow(self, api_client):
        """打回流程"""
        create_response = api_client.post("/issues", json={"title": "测试", "description": "描述"})
        issue_id = create_response.json()["issue"]["id"]

        # 触发 AI 执行
        api_client.post(f"/issues/{issue_id}/trigger", json={"stage": "brainstorm"})

        # 打回
        response = api_client.post(
            f"/issues/{issue_id}/stages/brainstorm/reject",
            json={"reason": "方案不够详细"}
        )
        assert response.status_code == 200
        data = response.json()["issue"]
        assert data["stages"]["brainstorm"]["status"] == "rejected"
