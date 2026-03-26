"""完整流水线 E2E 测试"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from swallowloop.interfaces.web.api.issues import router
from swallowloop.application.service import IssueService
from swallowloop.infrastructure.persistence import InMemoryIssueRepository
from tests.helpers import MockExecutor


@pytest.fixture
def client():
    """创建完整测试客户端"""
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


class TestFullLifecycle:
    """完整流水线端到端测试"""

    def test_issue_full_lifecycle(self, client):
        """测试从创建到归档的完整流程"""
        # 1. 创建 Issue
        response = client.post("/issues", json={
            "title": "新功能开发",
            "description": "开发一个很棒的功能"
        })
        assert response.status_code == 201
        issue_id = response.json()["issue"]["id"]

        # 2. 列出所有 Issue
        response = client.get("/issues")
        assert len(response.json()["issues"]) == 1

        # 3. 触发并审批通过头脑风暴
        client.post(f"/issues/{issue_id}/trigger", json={"stage": "brainstorm"})
        response = client.post(
            f"/issues/{issue_id}/stages/brainstorm/approve",
            json={"comment": "方案不错"}
        )
        assert response.status_code == 200
        assert response.json()["issue"]["currentStage"] == "planFormed"

        # 4. 触发并审批通过方案成型
        client.post(f"/issues/{issue_id}/trigger", json={"stage": "planFormed"})
        response = client.post(
            f"/issues/{issue_id}/stages/planFormed/approve",
            json={"comment": "计划合理"}
        )
        assert response.status_code == 200
        assert response.json()["issue"]["currentStage"] == "detailedDesign"

        # 5. 触发并打回详细设计
        client.post(f"/issues/{issue_id}/trigger", json={"stage": "detailedDesign"})
        response = client.post(
            f"/issues/{issue_id}/stages/detailedDesign/reject",
            json={"reason": "缺少错误处理"}
        )
        assert response.status_code == 200
        assert response.json()["issue"]["stages"]["detailedDesign"]["status"] == "rejected"

        # 6. 再次触发并审批通过
        client.post(f"/issues/{issue_id}/trigger", json={"stage": "detailedDesign"})
        response = client.post(
            f"/issues/{issue_id}/stages/detailedDesign/approve",
            json={"comment": "已补充"}
        )
        assert response.status_code == 200

        # 7. 归档
        response = client.patch(f"/issues/{issue_id}", json={"status": "archived"})
        assert response.status_code == 200
        assert response.json()["issue"]["status"] == "archived"

        # 8. 删除
        response = client.delete(f"/issues/{issue_id}")
        assert response.status_code == 200
