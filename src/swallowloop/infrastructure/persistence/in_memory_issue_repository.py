"""内存 Issue 仓库实现"""

import threading
from typing import Optional

from ...domain.model import Issue, IssueId, Stage, StageStatus
from ...domain.repository import IssueRepository


class InMemoryIssueRepository(IssueRepository):
    """
    纯内存 Issue 仓库（线程安全）

    所有数据存储在内存字典中，启动时为空。
    使用 threading.Lock 保证线程安全。
    """

    def __init__(self):
        self._issues: dict[str, Issue] = {}
        self._lock = threading.Lock()

    def get(self, issue_id: IssueId) -> Issue | None:
        with self._lock:
            return self._issues.get(str(issue_id))

    def save(self, issue: Issue) -> None:
        with self._lock:
            self._issues[str(issue.id)] = issue

    def list_all(self) -> list[Issue]:
        with self._lock:
            return list(self._issues.values())

    def list_active(self) -> list[Issue]:
        with self._lock:
            return [i for i in self._issues.values() if i.is_active]

    def delete(self, issue_id: IssueId) -> bool:
        with self._lock:
            return self._issues.pop(str(issue_id), None) is not None

    def list_stages_by_status(self, status: StageStatus) -> list[tuple[Issue, Stage]]:
        with self._lock:
            result = []
            for issue in list(self._issues.values()):
                if not issue.is_active:
                    continue
                for stage, state in issue.stages.items():
                    if state.status == status:
                        result.append((issue, stage))
            return result
