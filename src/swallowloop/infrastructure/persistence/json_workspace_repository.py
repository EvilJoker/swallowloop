"""JSON 工作空间仓库实现"""

import json
from datetime import datetime
from pathlib import Path

from ...domain.model import Workspace
from ...domain.repository import WorkspaceRepository


class JsonWorkspaceRepository(WorkspaceRepository):
    """
    JSON 文件工作空间仓库
    
    工作空间数据保存到 ~/.swallowloop/workspaces.json
    """
    
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".swallowloop"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_file = self.data_dir / "workspaces.json"
        
        # 加载已有工作空间
        self._workspaces: dict[str, dict] = self._load()
    
    def _load(self) -> dict:
        """加载工作空间数据"""
        if not self.workspaces_file.exists():
            return {}
        
        try:
            with open(self.workspaces_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save(self) -> None:
        """保存工作空间数据"""
        with open(self.workspaces_file, "w") as f:
            json.dump(self._workspaces, f, indent=2, ensure_ascii=False, default=str)
    
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
