"""代码库缓存管理"""

import subprocess
from pathlib import Path


class CodebaseManager:
    """代码库缓存管理器
    
    用于管理代码库的本地缓存，避免每次任务都重新克隆。
    缓存结构：~/.swallowloop/codebase/{owner}_{repo}/
    """
    
    def __init__(self, codebase_dir: Path, github_repo: str):
        """
        Args:
            codebase_dir: 缓存根目录
            github_repo: GitHub 仓库名 (owner/repo)
        """
        self.codebase_dir = codebase_dir
        self.github_repo = github_repo
        # 将 owner/repo 转换为 owner_repo 作为目录名
        self.repo_dir_name = github_repo.replace("/", "_")
        self.repo_path = codebase_dir / self.repo_dir_name
    
    def prepare_codebase(self, github_token: str) -> Path:
        """准备代码库缓存
        
        如果缓存不存在则克隆，存在则更新。
        
        Args:
            github_token: GitHub 访问令牌
            
        Returns:
            缓存仓库路径
        """
        self.codebase_dir.mkdir(parents=True, exist_ok=True)
        
        if self.repo_path.exists():
            # 已存在，执行 git pull 更新
            print(f"[Codebase] 更新缓存: {self.github_repo}")
            self._pull()
        else:
            # 不存在，执行 git clone
            print(f"[Codebase] 克隆仓库: {self.github_repo}")
            self._clone(github_token)
        
        return self.repo_path
    
    def _clone(self, github_token: str) -> None:
        """克隆仓库到缓存目录"""
        # 构建带认证的 URL
        repo_url = f"https://{github_token}@github.com/{self.github_repo}.git"
        
        result = subprocess.run(
            ["git", "clone", repo_url, str(self.repo_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"克隆仓库失败: {result.stderr}")
        
        print(f"[Codebase] 克隆完成: {self.repo_path}")
    
    def _pull(self) -> None:
        """更新缓存仓库"""
        result = subprocess.run(
            ["git", "fetch", "--all"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"[Codebase] fetch 警告: {result.stderr}")
        
        result = subprocess.run(
            ["git", "reset", "--hard", "origin/HEAD"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # 如果 origin/HEAD 不存在，尝试 main/master
            for branch in ["main", "master"]:
                result = subprocess.run(
                    ["git", "reset", "--hard", f"origin/{branch}"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    break
        
        print(f"[Codebase] 更新完成: {self.repo_path}")
    
    def copy_to_workspace(self, workspace_path: Path) -> Path:
        """将缓存仓库复制到工作空间
        
        使用 git clone --local 实现高效复制。
        
        Args:
            workspace_path: 目标工作空间路径
            
        Returns:
            工作空间仓库路径
        """
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        repo_workspace_path = workspace_path / self.repo_dir_name
        
        if repo_workspace_path.exists():
            print(f"[Codebase] 工作空间已存在: {repo_workspace_path}")
            return repo_workspace_path
        
        print(f"[Codebase] 复制到工作空间: {repo_workspace_path}")
        
        # 使用 git clone --local 从本地仓库克隆
        # --no-hardlinks 避免硬链接问题
        result = subprocess.run(
            ["git", "clone", "--local", str(self.repo_path), str(repo_workspace_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"复制仓库失败: {result.stderr}")
        
        return repo_workspace_path
