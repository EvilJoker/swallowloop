"""GitHub API 封装"""

import re
from dataclasses import dataclass
from typing import Optional

from github import Github, Issue, PullRequest, Repository

from .config import Config


@dataclass
class Task:
    """任务信息"""
    issue_number: int
    title: str
    body: str
    branch_name: str
    

class GitHubClient:
    """GitHub API 客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.github = Github(config.github_token)
        self.repo: Repository = self.github.get_repo(config.github_repo)
    
    def get_labeled_issues(self) -> list[Issue.Issue]:
        """获取带有指定标签的开放Issue"""
        issues = self.repo.get_issues(
            state="open",
            labels=[self.config.issue_label]
        )
        return list(issues)
    
    def create_branch(self, issue_number: int, title: str) -> str:
        """
        为Issue创建特性分支
        分支命名: Issue{number}_{slug}
        """
        # 生成slug: 只保留字母数字，空格转下划线
        slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
        slug = re.sub(r"[\s]+", "-", slug).strip("-")[:30]
        branch_name = f"Issue{issue_number}_{slug}"
        
        # 获取基础分支的引用
        base_ref = self.repo.get_ref(f"heads/{self.config.base_branch}")
        
        # 创建新分支
        self.repo.create_ref(
            f"refs/heads/{branch_name}",
            base_ref.object.sha
        )
        
        return branch_name
    
    def create_pr(
        self, 
        issue_number: int,
        branch_name: str, 
        title: str,
        body: str,
        existing_pr_number: int | None = None,
    ) -> PullRequest.PullRequest:
        """
        创建或获取Pull Request
        
        如果 existing_pr_number 存在，尝试获取现有PR
        如果PR不存在或已关闭，创建新PR
        """
        pr_title = f"Issue#{issue_number}: {title}"
        pr_body = f"""## 关联 Issue
Closes #{issue_number}

## 实现说明
{body}

---
*此PR由 SwallowLoop 自动生成*
"""
        
        # 先尝试获取现有PR
        if existing_pr_number:
            try:
                pr = self.repo.get_pull(existing_pr_number)
                if pr.state == "open":
                    # PR 存在且 open，直接返回
                    return pr
            except Exception:
                pass  # PR不存在，继续创建新的
        
        # 检查是否已有该分支的open PR
        try:
            pulls = self.repo.get_pulls(
                state="open",
                head=f"{self.repo.owner.login}:{branch_name}",
                base=self.config.base_branch
            )
            for pr in pulls:
                if pr.head.ref == branch_name:
                    # 已存在open PR，返回它
                    return pr
        except Exception:
            pass
        
        # 创建新PR
        pr = self.repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=self.config.base_branch,
            draft=False
        )
        
        return pr
    
    def comment_on_issue(self, issue_number: int, message: str) -> None:
        """在Issue上添加评论"""
        issue = self.repo.get_issue(issue_number)
        issue.create_comment(message)
    
    def get_issue(self, issue_number: int) -> Issue.Issue:
        """获取指定Issue"""
        return self.repo.get_issue(issue_number)
    
    def has_branch(self, branch_name: str) -> bool:
        """检查分支是否存在"""
        try:
            self.repo.get_ref(f"heads/{branch_name}")
            return True
        except Exception:
            return False
