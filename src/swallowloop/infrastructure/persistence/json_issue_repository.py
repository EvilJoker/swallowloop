"""JSON Issue 仓库实现"""

import fcntl
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import IO

from ...domain.model import Issue, IssueId, Stage, StageStatus, IssueStatus, TodoStatus, ExecutionState
from ...domain.repository import IssueRepository

logger = logging.getLogger(__name__)


class JsonIssueRepository(IssueRepository):
    """
    JSON 文件 Issue 仓库

    数据保存到 ~/.swallowloop/{project}/issues.json
    使用文件锁保护并发写入
    """

    def __init__(self, project: str, data_dir: Path | None = None):
        self.project = project
        self.data_dir = (data_dir or Path.home() / ".swallowloop") / project
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.issues_file = self.data_dir / "issues.json"
        self._lock_file = self.data_dir / "issues.json.lock"
        self._load()

    def _load(self) -> None:
        """加载数据"""
        if not self.issues_file.exists():
            self._data = {"issues": []}
            return

        try:
            with open(self.issues_file) as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载 Issue 数据失败: {e}")
            self._data = {"issues": []}

    def _save(self) -> None:
        """保存数据（带文件锁）"""
        temp_file = self.issues_file.with_suffix('.tmp')
        lock_path = self._lock_file

        try:
            with open(lock_path, 'w') as lock_f:
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
                try:
                    with open(temp_file, "w") as f:
                        json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)
                    temp_file.replace(self.issues_file)
                finally:
                    fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"保存 Issue 数据失败: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def get(self, issue_id: IssueId) -> Issue | None:
        """根据 ID 获取 Issue"""
        for data in self._data.get("issues", []):
            if data["id"] == str(issue_id):
                return self._deserialize(data)
        return None

    def save(self, issue: Issue) -> None:
        """保存 Issue"""
        issues = self._data.get("issues", [])
        for i, data in enumerate(issues):
            if data["id"] == str(issue.id):
                issues[i] = self._serialize(issue)
                break
        else:
            issues.append(self._serialize(issue))
        self._data["issues"] = issues
        self._save()

    def list_all(self) -> list[Issue]:
        """列出所有 Issue"""
        return [self._deserialize(d) for d in self._data.get("issues", [])]

    def list_active(self) -> list[Issue]:
        """列出活跃 Issue"""
        return [i for i in self.list_all() if i.is_active]

    def delete(self, issue_id: IssueId) -> bool:
        """删除 Issue"""
        issues = self._data.get("issues", [])
        original_len = len(issues)
        self._data["issues"] = [d for d in issues if d["id"] != str(issue_id)]
        if len(self._data["issues"]) < original_len:
            self._save()
            return True
        return False

    def _serialize(self, issue: Issue) -> dict:
        """序列化 Issue"""
        return {
            "id": str(issue.id),
            "title": issue.title,
            "description": issue.description,
            "status": issue.status.value,
            "currentStage": issue.current_stage.value,
            "createdAt": issue.created_at.isoformat(),
            "archivedAt": issue.archived_at.isoformat() if issue.archived_at else None,
            "discardedAt": issue.discarded_at.isoformat() if issue.discarded_at else None,
            "stages": {
                stage.value: {
                    "stage": stage.value,
                    "status": state.status.value,
                    "document": state.document,
                    "comments": [
                        {
                            "id": c.id,
                            "stage": c.stage.value,
                            "action": c.action,
                            "content": c.content,
                            "createdAt": c.created_at.isoformat(),
                        }
                        for c in state.comments
                    ],
                    "startedAt": state.started_at.isoformat() if state.started_at else None,
                    "completedAt": state.completed_at.isoformat() if state.completed_at else None,
                    "todoList": [
                        {"id": t.id, "content": t.content, "status": t.status.value}
                        for t in (state.todo_list or [])
                    ],
                    "progress": state.progress,
                    "executionState": state.execution_state.value if state.execution_state else None,
                }
                for stage, state in issue.stages.items()
            },
        }

    def _deserialize(self, data: dict) -> Issue:
        """反序列化 Issue"""
        from ...domain.model import StageState, TodoItem, ReviewComment

        stages = {}
        for stage_str, state_data in data.get("stages", {}).items():
            stage = Stage(stage_str)
            todo_list = None
            if state_data.get("todoList"):
                todo_list = [
                    TodoItem(
                        id=t["id"],
                        content=t["content"],
                        status=TodoStatus(t["status"]),
                    )
                    for t in state_data["todoList"]
                ]

            comments = []
            for c in state_data.get("comments", []):
                comments.append(ReviewComment(
                    id=c["id"],
                    stage=Stage(c["stage"]),
                    action=c["action"],
                    content=c["content"],
                    created_at=datetime.fromisoformat(c["createdAt"]),
                ))

            execution_state = None
            if state_data.get("executionState"):
                execution_state = ExecutionState(state_data["executionState"])

            stages[stage] = StageState(
                stage=stage,
                status=StageStatus(state_data.get("status", "pending")),
                document=state_data.get("document", ""),
                comments=comments,
                started_at=datetime.fromisoformat(state_data["startedAt"]) if state_data.get("startedAt") else None,
                completed_at=datetime.fromisoformat(state_data["completedAt"]) if state_data.get("completedAt") else None,
                todo_list=todo_list,
                progress=state_data.get("progress"),
                execution_state=execution_state,
            )

        issue = Issue(
            id=IssueId(data["id"]),
            title=data["title"],
            description=data.get("description", ""),
            status=IssueStatus(data.get("status", "active")),
            current_stage=Stage(data.get("currentStage", "brainstorm")),
            created_at=datetime.fromisoformat(data["createdAt"]) if data.get("createdAt") else datetime.now(),
            archived_at=datetime.fromisoformat(data["archivedAt"]) if data.get("archivedAt") else None,
            discarded_at=datetime.fromisoformat(data["discardedAt"]) if data.get("discardedAt") else None,
            stages=stages,
        )
        return issue
