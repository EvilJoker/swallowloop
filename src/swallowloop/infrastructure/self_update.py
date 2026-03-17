"""SwallowLoop 自更新模块

实现版本监控和自动更新功能：
1. 定期检查远程是否有新版本
2. 如果有新版本，执行 git pull
3. 使用 exec 替换当前进程
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SelfUpdater:
    """
    自更新器
    
    负责检查远程版本更新并自动更新 SwallowLoop
    """
    
    def __init__(self, repo_path: Path | None = None, check_interval: int = 300):
        """
        初始化
        
        Args:
            repo_path: SwallowLoop 仓库路径，默认自动检测
            check_interval: 检查更新的间隔（秒）
        """
        self._repo_path = repo_path or self._find_repo_path()
        self._check_interval = check_interval
        self._last_check_time: datetime | None = None
        self._current_commit: str | None = None
    
    def _find_repo_path(self) -> Path:
        """查找 SwallowLoop 仓库路径"""
        # 从当前模块位置向上查找
        current = Path(__file__).resolve()
        
        # 向上遍历直到找到 .git 目录
        for parent in current.parents:
            if (parent / ".git").exists():
                # 检查是否是 swallowloop 仓库
                if (parent / "src" / "swallowloop").exists():
                    return parent
        
        # 回退到当前工作目录
        return Path.cwd()
    
    def _get_current_commit(self) -> str:
        """获取当前 commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"获取当前 commit 失败: {e}")
            return ""
    
    def _get_remote_commit(self, branch: str = "main") -> str:
        """获取远程分支的最新 commit hash"""
        try:
            # 先 fetch
            subprocess.run(
                ["git", "fetch", "origin", branch],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            
            # 获取远程 commit
            result = subprocess.run(
                ["git", "rev-parse", f"origin/{branch}"],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"获取远程 commit 失败: {e}")
            return ""
    
    def _get_current_branch(self) -> str:
        """获取当前分支名"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "main"
    
    def should_check(self) -> bool:
        """检查是否应该进行版本检查"""
        if self._last_check_time is None:
            return True
        
        elapsed = (datetime.now() - self._last_check_time).total_seconds()
        return elapsed >= self._check_interval
    
    def check_for_update(self) -> bool:
        """
        检查是否有新版本
        
        Returns:
            True 如果有新版本可用
        """
        if not self.should_check():
            return False
        
        self._last_check_time = datetime.now()
        
        # 获取当前和远程 commit
        current = self._get_current_commit()
        remote = self._get_remote_commit()
        
        if not current or not remote:
            logger.warning("无法获取版本信息，跳过更新检查")
            return False
        
        self._current_commit = current
        
        if current != remote:
            logger.info(f"发现新版本: {current[:8]} -> {remote[:8]}")
            return True
        
        logger.debug("当前已是最新版本")
        return False
    
    def perform_update(self) -> bool:
        """
        执行更新操作
        
        1. git pull 获取最新代码
        2. 返回 True 表示需要重启
        
        Returns:
            True 如果更新成功且需要重启
        """
        branch = self._get_current_branch()
        logger.info(f"开始更新: branch={branch}")
        
        try:
            # 执行 git pull
            result = subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=self._repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"git pull 完成: {result.stdout.strip()}")
            
            # 检查是否有实际更新
            new_commit = self._get_current_commit()
            if new_commit == self._current_commit:
                logger.info("没有实际更新，继续运行")
                return False
            
            logger.info(f"更新成功: {self._current_commit[:8]} -> {new_commit[:8]}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"更新失败: {e.stderr}")
            return False
    
    def restart(self) -> None:
        """
        重启 SwallowLoop
        
        使用 exec 替换当前进程
        """
        logger.info("正在重启 SwallowLoop...")
        
        # 获取可执行文件路径
        executable = sys.executable
        args = sys.argv
        
        logger.info(f"exec: {executable} {' '.join(args)}")
        
        # 使用 exec 替换当前进程
        os.execv(executable, [executable] + args)
