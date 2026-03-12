"""代码空间管理器"""

import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import Config
from .models import Workspace


class WorkspaceManager:
    """
    代码空间管理器
    
    负责：
    - 创建/销毁代码空间
    - 跟踪活跃的代码空间
    - 代码空间分配与回收
    
    空间命名格式: issue{issue_number}_{repo_name}_{date}
    例如: issue1_hubble-pad_20260312
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.base_dir = config.work_dir or Path.home() / ".swallowloop" / "workspaces"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 活跃的工作空间 {issue_number: Workspace}
        self._workspaces: dict[int, Workspace] = {}
    
    def allocate(self, issue_number: int, branch_name: str) -> Workspace:
        """
        为 Issue 分配代码空间
        
        Args:
            issue_number: Issue 编号
            branch_name: 分支名
            
        Returns:
            Workspace 代码空间
        """
        # 从 repo 配置提取仓库名
        repo_name = self.config.github_repo.split("/")[-1]
        repo_name = re.sub(r"[^a-zA-Z0-9_-]", "-", repo_name)
        
        # 日期格式: YYYYMMDD
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 空间ID: issue{issue_number}_{repo_name}_{date}
        workspace_id = f"issue{issue_number}_{repo_name}_{date_str}"
        workspace_path = self.base_dir / workspace_id
        
        workspace = Workspace(
            id=workspace_id,
            issue_number=issue_number,
            branch_name=branch_name,
            path=workspace_path,
        )
        
        # 创建空间目录（如果不存在）
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        self._workspaces[issue_number] = workspace
        return workspace
    
    def get(self, issue_number: int) -> Optional[Workspace]:
        """获取 Issue 的代码空间"""
        return self._workspaces.get(issue_number)
    
    def release(self, issue_number: int) -> bool:
        """
        释放代码空间
        
        Args:
            issue_number: Issue 编号
            
        Returns:
            是否成功释放
        """
        workspace = self._workspaces.get(issue_number)
        if not workspace:
            return False
        
        # 删除本地目录
        if workspace.path.exists():
            try:
                # 删除整个工作空间目录（包含仓库）
                workspace_root = workspace.path.parent  # ws-{issue_number} 目录
                shutil.rmtree(workspace_root)
            except Exception:
                pass
        
        # 从跟踪中移除
        del self._workspaces[issue_number]
        return True
    
    def list_active(self) -> list[Workspace]:
        """列出所有活跃的代码空间"""
        return list(self._workspaces.values())
    
    def cleanup_stale(self, max_age_hours: int = 24) -> int:
        """
        清理过期的代码空间
        
        Args:
            max_age_hours: 最大存活时间（小时）
            
        Returns:
            清理的数量
        """
        now = datetime.now()
        cleaned = 0
        
        for ws in list(self._workspaces.values()):
            age = now - ws.created_at
            if age > timedelta(hours=max_age_hours):
                self.release(ws.issue_number)
                cleaned += 1
        
        return cleaned
