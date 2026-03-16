"""源码控制抽象基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class IssueInfo:
    """Issue 信息"""
    number: int
    title: str
    body: str
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PullRequestInfo:
    """Pull Request 信息"""
    number: int
    html_url: str
    branch_name: str
    title: str
    body: str = ""
    state: str = "open"


@dataclass
class CommentInfo:
    """评论信息"""
    id: int
    body: str
    author: str
    created_at: datetime = field(default_factory=datetime.now)


class SourceControl(ABC):
    """
    源码控制接口
    
    定义与代码托管平台交互的抽象操作
    """
    
    @abstractmethod
    def get_labeled_issues(self, label: str) -> list[IssueInfo]:
        """获取带有指定标签的开放 Issue"""
        pass
    
    @abstractmethod
    def get_issue(self, issue_number: int) -> IssueInfo:
        """获取指定 Issue"""
        pass
    
    @abstractmethod
    def get_issue_comments(self, issue_number: int) -> list[CommentInfo]:
        """获取 Issue 评论"""
        pass
    
    @abstractmethod
    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PullRequestInfo:
        """创建 Pull Request"""
        pass
    
    @abstractmethod
    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """获取指定 Pull Request"""
        pass
    
    @abstractmethod
    def comment_on_issue(self, issue_number: int, body: str) -> None:
        """在 Issue 上添加评论"""
        pass
    
    @abstractmethod
    def has_branch(self, branch_name: str) -> bool:
        """检查分支是否存在"""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供商名称"""
        pass
