"""JSON 工作空间仓库实现"""

import fcntl
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import IO

from ...domain.model import Workspace
from ...domain.repository import WorkspaceRepository


logger = logging.getLogger(__name__)


class JsonWorkspaceRepository(WorkspaceRepository):
    """
    JSON 文件工作空间仓库
    
    工作空间数据保存到 ~/.swallowloop/workspaces.json
    使用文件锁保护并发写入
    """
    
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".swallowloop"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_file = self.data_dir / "workspaces.json"
        self._lock_file = self.data_dir / "workspaces.json.lock"
        
        # 加载已有工作空间
        self._workspaces: dict[str, dict] = self._load()
    
    def _acquire_lock(self, lock_file: IO) -> None:
        """获取文件锁"""
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    
    def _release_lock(self, lock_file: IO) -> None:
        """释放文件锁"""
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    
    def _load(self) -> dict:
        """加载工作空间数据"""
        if not self.workspaces_file.exists():
            return {}
        
        try:
            with open(self.workspaces_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"加载工作空间数据失败: {e}")
            return {}
    
    def _save(self) -> None:
        """保存工作空间数据（带文件锁保护）"""
        # 先写入临时文件，再原子替换
        temp_file = self.workspaces_file.with_suffix('.tmp')
        lock_path = self._lock_file
        
        try:
            # 获取文件锁
            with open(lock_path, 'w') as lock_f:
                self._acquire_lock(lock_f)
                try:
                    # 写入临时文件
                    with open(temp_file, "w") as f:
                        json.dump(self._workspaces, f, indent=2, ensure_ascii=False, default=str)
                    
                    # 原子替换
                    temp_file.replace(self.workspaces_file)
                finally:
                    self._release_lock(lock_f)
        except Exception as e:
            logger.error(f"保存工作空间数据失败: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise
        finally:
            # 清理锁文件
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except:
                    pass
    
    def get(self, issue_number: int) -> Workspace | None:
        """获取Issue的工作空间"""
        data = self._workspaces.get(str(issue_number))
        if not data:
            return None
        return self._deserialize(data)
    
    def save(self, workspace: Workspace) -> None:
        """保存工作空间"""
        self._workspaces[str(workspace.issue_number)] = self._serialize(workspace)
        self._save()
    
    def release(self, issue_number: int) -> bool:
        """释放工作空间"""
        if str(issue_number) in self._workspaces:
            del self._workspaces[str(issue_number)]
            self._save()
            return True
        return False
    
    def list_active(self) -> list[Workspace]:
        """列出活跃工作空间"""
        return [
            self._deserialize(data)
            for data in self._workspaces.values()
        ]
    
    def list_expired(self, days: int = 7) -> list[Workspace]:
        """列出过期的工作空间（创建时间超过指定天数）"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        
        return [
            self._deserialize(data)
            for data in self._workspaces.values()
            if datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())) < cutoff
        ]
    
    def delete(self, workspace_id: str) -> bool:
        """删除工作空间记录"""
        # 根据 workspace_id 查找
        for issue_number, data in list(self._workspaces.items()):
            if data.get("id") == workspace_id:
                del self._workspaces[issue_number]
                self._save()
                return True
        return False
    
    def _serialize(self, workspace: Workspace) -> dict:
        """序列化工作空间"""
        return {
            "id": workspace.id,
            "issue_number": workspace.issue_number,
            "branch_name": workspace.branch_name,
            "path": str(workspace.path),
            "pr_number": workspace.pr_number,
            "created_at": workspace.created_at.isoformat(),
        }
    
    def _deserialize(self, data: dict) -> Workspace:
        """反序列化工作空间"""
        return Workspace(
            id=data["id"],
            issue_number=data["issue_number"],
            branch_name=data["branch_name"],
            path=Path(data["path"]),
            pr_number=data.get("pr_number"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
        )
