"""持久化"""

MODULE_NAME = "infrastructure.persistence"

from .in_memory_issue_repository import InMemoryIssueRepository

__all__ = [
    "MODULE_NAME",
    "InMemoryIssueRepository",
]
