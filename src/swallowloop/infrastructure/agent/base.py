"""Agent 抽象基类"""

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.model import Task
    from ..codebase import CodebaseManager

# 任务报告文件名
REPORT_FILENAME = ".swallowloop_report.md"


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    message: str
    files_changed: list[str] = field(default_factory=list)
    output: str = ""


class Agent(ABC):
    """
    代码生成代理接口
    
    定义执行任务生成代码的抽象操作
    """
    
    @abstractmethod
    def execute(
        self,
        task: "Task",
        workspace_path: Path,
    ) -> ExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务对象
            workspace_path: 工作空间路径
            
        Returns:
            ExecutionResult 执行结果
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """代理名称"""
        pass
    
    @staticmethod
    @abstractmethod
    def check_available() -> tuple[bool, str]:
        """检查代理是否可用"""
        pass
    
    # ==================== 公共 Git 操作 ====================
    
    @staticmethod
    def _run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
        """执行 git 命令"""
        return subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )
    
    @classmethod
    def _prepare_repo(
        cls,
        task: "Task",
        workspace_path: Path,
        codebase_manager: "CodebaseManager | None" = None,
        github_token: str | None = None,
    ) -> ExecutionResult:
        """准备仓库
        
        如果提供了 codebase_manager 和 github_token，使用缓存机制：
        1. 检查 codebase 缓存是否存在
        2. 不存在则克隆，存在则更新
        3. 从缓存复制到工作空间
        
        否则使用传统方式直接克隆。
        """
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        git_dir = workspace_path / ".git"
        if git_dir.exists():
            # 工作空间已有仓库，更新即可
            try:
                cls._run_git(["fetch", "origin"], workspace_path)
                cls._run_git(["checkout", "main"], workspace_path)
                cls._run_git(["pull", "origin", "main"], workspace_path)
            except subprocess.CalledProcessError as e:
                return ExecutionResult(False, f"更新仓库失败: {e.stderr or str(e)}")
            return ExecutionResult(True, "仓库准备完成")
        
        # 使用 CodebaseManager 缓存机制
        if codebase_manager and github_token:
            try:
                # 1. 准备缓存仓库
                codebase_manager.prepare_codebase(github_token)
                # 2. 复制到工作空间（直接复制到 workspace_path）
                codebase_manager.copy_to_workspace(workspace_path)
            except Exception as e:
                return ExecutionResult(False, f"缓存复制失败: {str(e)}")
            return ExecutionResult(True, "仓库准备完成（使用缓存）")
        
        # 传统方式：直接克隆
        try:
            cls._run_git(["clone", task.repo_url, "."], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"克隆仓库失败: {e.stderr or str(e)}")
        return ExecutionResult(True, "仓库准备完成")
    
    @classmethod
    def _setup_branch(cls, task: "Task", workspace_path: Path) -> ExecutionResult:
        """设置分支"""
        try:
            result = cls._run_git(["checkout", task.branch_name], workspace_path, check=False)
            if result.returncode != 0:
                cls._run_git(["checkout", "-b", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"分支操作失败: {e.stderr or str(e)}")
        return ExecutionResult(True, "分支设置完成")
    
    @classmethod
    def _get_changed_files(cls, repo_path: Path) -> list[str]:
        """获取所有变化的文件（包括未跟踪的）"""
        try:
            result = cls._run_git(["status", "--porcelain"], repo_path)
            files = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line[3:].split(" -> ")
                    if len(parts) == 2:
                        files.append(parts[1].strip())
                    else:
                        files.append(line[3:].strip())
            return [f for f in files if f]
        except subprocess.CalledProcessError:
            return []
    
    @classmethod
    def _commit_and_push(cls, task: "Task", workspace_path: Path, files_changed: list[str]) -> ExecutionResult:
        """提交并推送"""
        try:
            cls._run_git(["add", "-A"], workspace_path)
            cls._run_git(["commit", "-m", f"Issue#{task.issue_number}: {task.title}"], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"提交失败: {e.stderr or str(e)}", files_changed)
        
        try:
            cls._run_git(["push", "-u", "origin", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"推送失败: {e.stderr or str(e)}", files_changed)
        
        return ExecutionResult(True, "任务完成，等待 PR 创建", files_changed)
    
    @classmethod
    def _prepare_revision(cls, task: "Task", workspace_path: Path) -> ExecutionResult:
        """准备修改任务（切换分支并拉取最新）
        
        支持浅克隆仓库：fetch 时指定深度获取远程分支
        """
        try:
            # 先尝试直接 fetch（完整仓库）
            result = cls._run_git(["fetch", "origin"], workspace_path, check=False)
            if result.returncode != 0:
                # 可能是浅克隆，尝试 fetch 指定分支
                result = cls._run_git(
                    ["fetch", "--depth", "1", "origin", task.branch_name],
                    workspace_path,
                    check=False
                )
            
            cls._run_git(["checkout", task.branch_name], workspace_path)
            cls._run_git(["reset", "--hard", f"origin/{task.branch_name}"], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"切换分支失败: {e.stderr or str(e)}")
        return ExecutionResult(True, "分支切换完成")
    
    @classmethod
    def _amend_and_push(cls, task: "Task", workspace_path: Path, files_changed: list[str]) -> ExecutionResult:
        """Amend 提交并强制推送"""
        try:
            cls._run_git(["add", "-A"], workspace_path)
            cls._run_git(["commit", "--amend", "--no-edit"], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"Amend 提交失败: {e.stderr or str(e)}", files_changed)
        
        try:
            cls._run_git(["push", "-f", "origin", task.branch_name], workspace_path)
        except subprocess.CalledProcessError as e:
            return ExecutionResult(False, f"强制推送失败: {e.stderr or str(e)}", files_changed)
        
        return ExecutionResult(True, "修改完成", files_changed)
    
    @staticmethod
    def _build_prompt(task: "Task") -> str:
        """构建任务提示"""
        from ...domain.model import TaskType
        
        if task.task_type == TaskType.REVISION:
            latest_comment = task.latest_comment
            feedback = latest_comment.body if latest_comment else task.description
            return f"""根据审核反馈修改代码:

**Issue:** {task.title}

**反馈内容:**
{feedback}

请根据反馈修改相关代码，确保满足审核要求。修改完成后，请确保代码可以正常运行。"""
        else:
            return f"""请解决以下 GitHub Issue:

**标题:** {task.title}

**描述:**
{task.description}

请:
1. 分析问题
2. 修改相关代码
3. 确保修改符合项目现有风格
4. 确保代码可以正常运行

完成后请总结你做的修改。"""
    
    @classmethod
    def generate_report(
        cls,
        task: "Task",
        workspace_path: Path,
        result: ExecutionResult,
        pr_url: str | None = None,
    ) -> None:
        """生成/更新任务执行报告
        
        Args:
            task: 任务对象
            workspace_path: 工作空间路径
            result: 执行结果
            pr_url: PR 链接（如果有）
        """
        from ...domain.model import TaskType
        
        report_path = workspace_path / REPORT_FILENAME
        
        # 确保 .gitignore 中包含报告文件
        cls._ensure_gitignore(workspace_path)
        
        # 读取现有报告（如果存在）
        existing_content = ""
        if report_path.exists():
            existing_content = report_path.read_text(encoding="utf-8")
        
        # 解析现有报告中的执行历史
        history = cls._parse_history(existing_content)
        
        # 添加新的执行记录
        new_record = cls._format_execution_record(task, result, pr_url, workspace_path)
        history.append(new_record)
        
        # 生成完整报告
        report_content = cls._build_report_content(task, history, result, pr_url)
        
        # 写入报告
        report_path.write_text(report_content, encoding="utf-8")
        print(f"[Report] 报告已更新: {report_path}")
    
    @staticmethod
    def _ensure_gitignore(workspace_path: Path) -> None:
        """确保 .gitignore 中包含报告文件"""
        gitignore_path = workspace_path / ".gitignore"
        
        gitignore_content = ""
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text(encoding="utf-8")
        
        # 检查是否已包含报告文件
        if REPORT_FILENAME not in gitignore_content:
            # 添加到 .gitignore
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if gitignore_content and not gitignore_content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n# SwallowLoop task report\n{REPORT_FILENAME}\n")
            print(f"[Report] 已添加 {REPORT_FILENAME} 到 .gitignore")
    
    @staticmethod
    def _parse_history(content: str) -> list[str]:
        """解析现有报告中的执行历史"""
        history = []
        in_history = False
        current_record = []
        
        for line in content.split("\n"):
            if line.startswith("## 执行历史"):
                in_history = True
                continue
            if in_history and line.startswith("### ") and "执行 #" in line:
                if current_record:
                    history.append("\n".join(current_record))
                current_record = [line]
            elif in_history and line.startswith("---"):
                if current_record:
                    history.append("\n".join(current_record))
                break
            elif in_history and current_record:
                current_record.append(line)
        
        return history
    
    @staticmethod
    def _get_diff_summary(workspace_path: Path, files_changed: list[str]) -> str:
        """获取代码变更摘要"""
        summary = ""
        
        for file_path in files_changed:
            full_path = workspace_path / file_path
            if not full_path.exists():
                continue
            
            # 获取文件状态
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD", "--", file_path],
                cwd=workspace_path,
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                summary += f"**{file_path}**\n```\n{result.stdout.strip()}\n```\n\n"
        
        # 获取整体 diff（限制大小）
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            diff = result.stdout.strip()
            # 限制 diff 大小
            if len(diff) > 5000:
                diff = diff[:5000] + "\n... (已截断，完整 diff 请查看 git)"
            summary += f"<details>\n<summary>查看完整 diff</summary>\n\n```diff\n{diff}\n```\n</details>\n"
        
        return summary or "_无代码变更记录_"
    
    @staticmethod
    def _format_execution_record(
        task: "Task",
        result: ExecutionResult,
        pr_url: str | None,
        workspace_path: Path | None = None,
    ) -> str:
        """格式化单次执行记录"""
        from ...domain.model import TaskType
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_type = "新任务" if task.task_type == TaskType.NEW_TASK else "修改"
        status = "✅ 成功" if result.success else "❌ 失败"
        
        record = f"""### 执行 #{task.submission_count + 1}

- **时间**: {timestamp}
- **类型**: {task_type}
- **状态**: {status}
- **消息**: {result.message}"""
        
        if pr_url:
            record += f"\n- **PR**: {pr_url}"
        
        # 修改文件列表
        if result.files_changed:
            record += f"\n\n#### 📁 修改文件\n\n"
            for f in result.files_changed:
                record += f"- `{f}`\n"
        
        # 代码变更详情
        if workspace_path and result.files_changed:
            record += "\n#### 📝 代码变更\n\n"
            record += Agent._get_diff_summary(workspace_path, result.files_changed)
        
        # Agent 输出（思路和实现）
        if result.output:
            record += f"\n#### 🤖 Agent 思路与实现\n\n"
            record += f"<details>\n<summary>点击展开 Agent 输出</summary>\n\n```\n{result.output}\n```\n</details>\n"
        
        return record
    
    @staticmethod
    def _build_report_content(
        task: "Task",
        history: list[str],
        result: ExecutionResult,
        pr_url: str | None,
    ) -> str:
        """构建完整报告内容"""
        from ...domain.model import TaskType
        
        task_type = "新任务" if task.task_type == TaskType.NEW_TASK else "修改"
        status = "✅ 成功" if result.success else "❌ 失败"
        
        content = f"""# SwallowLoop 任务报告

> 此报告由 SwallowLoop 自动生成，记录任务执行情况

## 任务信息

| 项目 | 值 |
|------|-----|
| Issue | #{task.issue_number} |
| 标题 | {task.title} |
| 类型 | {task_type} |
| 分支 | {task.branch_name} |
| 当前状态 | {status} |
| 重试次数 | {task.retry_count}/{task._max_retries} |
"""
        
        if pr_url:
            content += f"| PR | {pr_url} |\n"
        
        content += f"""
## 任务描述

{task.description or "_无描述_"}

## 执行历史

"""
        
        # 添加执行历史（最新的在前）
        for record in reversed(history):
            content += record + "\n\n"
        
        content += """---

*此文件不应提交到版本控制，已在 .gitignore 中忽略*
"""
        
        return content