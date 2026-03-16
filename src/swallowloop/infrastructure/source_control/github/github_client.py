"""GitHub 源码控制实现"""

import re
from typing import Any

from github import Github, Issue, PullRequest, Repository

from ..base import SourceControl, IssueInfo, PullRequestInfo, CommentInfo


class GitHubSourceControl(SourceControl):
    """
    GitHub 源码控制实现
    
    使用 PyGithub 库与 GitHub API 交互
    """
    
    def __init__(self, token: str, repo: str):
        """
        初始化
        
        Args:
            token: GitHub Personal Access Token
            repo: 仓库名称 (owner/repo 格式)
        """
        self._token = token
        self._repo_name = repo
        self._github = Github(token)
        self._repo: Repository | None = None
    
    @property
    def repo(self) -> Repository:
        """延迟加载仓库对象"""
        if self._repo is None:
            self._repo = self._github.get_repo(self._repo_name)
        return self._repo
    
    @property
    def provider_name(self) -> str:
        return "github"
    
    def get_labeled_issues(self, label: str) -> list[IssueInfo]:
        """获取带有指定标签的开放 Issue"""
        issues = self.repo.get_issues(state="open", labels=[label])
        return [
            IssueInfo(
                number=issue.number,
                title=issue.title,
                body=issue.body or "",
                state=issue.state,
                labels=[l.name for l in issue.labels],
                created_at=issue.created_at,
                updated_at=issue.updated_at,
            )
            for issue in issues
        ]
    
    def get_issue(self, issue_number: int) -> IssueInfo:
        """获取指定 Issue"""
        issue = self.repo.get_issue(issue_number)
        return IssueInfo(
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            state=issue.state,
            labels=[l.name for l in issue.labels],
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )
    
    def get_issue_comments(self, issue_number: int) -> list[CommentInfo]:
        """获取 Issue 评论"""
        issue = self.repo.get_issue(issue_number)
        return [
            CommentInfo(
                id=comment.id,
                body=comment.body or "",
                author=comment.user.login if comment.user else "unknown",
                created_at=comment.created_at,
            )
            for comment in issue.get_comments()
        ]
    
    def create_pull_request(
        self,
        branch_name: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PullRequestInfo:
        """创建 Pull Request"""
        # 检查是否已有该分支的 open PR
        try:
            pulls = self.repo.get_pulls(
                state="open",
                head=f"{self.repo.owner.login}:{branch_name}",
                base=base_branch
            )
            for pr in pulls:
                if pr.head.ref == branch_name:
                    # 已存在 open PR，返回它
                    return PullRequestInfo(
                        number=pr.number,
                        html_url=pr.html_url,
                        branch_name=branch_name,
                        title=pr.title,
                        body=pr.body or "",
                        state=pr.state,
                    )
        except Exception:
            pass
        
        # 创建新 PR
        pr = self.repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
            draft=False
        )
        
        return PullRequestInfo(
            number=pr.number,
            html_url=pr.html_url,
            branch_name=branch_name,
            title=pr.title,
            body=pr.body or "",
            state=pr.state,
        )
    
    def get_pull_request(self, pr_number: int) -> PullRequestInfo:
        """获取指定 Pull Request"""
        pr = self.repo.get_pull(pr_number)
        return PullRequestInfo(
            number=pr.number,
            html_url=pr.html_url,
            branch_name=pr.head.ref,
            title=pr.title,
            body=pr.body or "",
            state=pr.state,
            merged=pr.merged or False,
        )
    
    def comment_on_issue(self, issue_number: int, body: str) -> None:
        """在 Issue 上添加评论"""
        issue = self.repo.get_issue(issue_number)
        issue.create_comment(body)
    
    def has_branch(self, branch_name: str) -> bool:
        """检查分支是否存在"""
        try:
            self.repo.get_ref(f"heads/{branch_name}")
            return True
        except Exception:
            return False
    
    def get_clone_url_with_token(self) -> str:
        """获取带 token 认证的 clone URL"""
        return f"https://{self._token}@github.com/{self._repo_name}.git"
