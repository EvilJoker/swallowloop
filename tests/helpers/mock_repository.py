"""测试辅助 - Mock Repository"""

from swallowloop.domain.model import Issue, IssueId, Stage, StageStatus
from swallowloop.domain.repository import IssueRepository


class MockRepository(IssueRepository):
    """内存实现的 Issue 仓库（用于测试）"""

    def __init__(self):
        self._issues = {}
        self._save_count = 0

    def get(self, issue_id: IssueId) -> Issue | None:
        return self._issues.get(str(issue_id))

    def save(self, issue: Issue) -> None:
        self._issues[str(issue.id)] = issue
        self._save_count += 1

    def list_all(self) -> list[Issue]:
        return list(self._issues.values())

    def list_active(self) -> list[Issue]:
        return [i for i in self._issues.values() if i.is_active]

    def delete(self, issue_id: IssueId) -> bool:
        key = str(issue_id)
        if key in self._issues:
            del self._issues[key]
            return True
        return False

    def list_stages_by_status(self, status: StageStatus) -> list[tuple[Issue, Stage]]:
        result = []
        for issue in self.list_active():
            for stage, state in issue.stages.items():
                if state.status == status:
                    result.append((issue, stage))
        return result
