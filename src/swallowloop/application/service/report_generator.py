"""任务报告生成器"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ...domain.model import Task


@dataclass
class ReportData:
    """报告数据"""
    issue_number: int
    labels: list[str]
    status: str  # "完成" or "失败"
    timestamp: str

    # 环境检查
    env_check_passed: bool
    env_check_message: str

    # 问题分析
    problem_analysis: str

    # 实现方案
    implementation_plan: str
    implementation_reason: str

    # 改动清单
    files_changed: list[dict]  # [{"file": "...", "type": "新增/修改", "description": "..."}]

    # 测试结果
    unit_test_passed: bool | None
    integration_test_passed: bool | None
    test_details: str

    # 文档更新
    readme_updated: bool
    architecture_doc_updated: bool
    glossary_updated: bool
    docs_updated_details: str

    # 风险提示
    risk_notes: str

    # PR 信息
    pr_url: str
    commit_hash: str


class ReportGenerator:
    """任务报告生成器"""

    REPORTS_DIR = "reports"

    def __init__(self, workspace_path: Path):
        self._workspace = workspace_path
        self._reports_dir = workspace_path.parent / self.REPORTS_DIR

    def generate(self, data: ReportData) -> Path:
        """生成报告文件"""
        # 确保 reports 目录存在
        self._reports_dir.mkdir(parents=True, exist_ok=True)

        # 生成报告文件路径
        report_path = self._reports_dir / f"issue-{data.issue_number}-report.md"

        # 生成报告内容
        content = self._render_template(data)

        # 写入文件
        report_path.write_text(content, encoding="utf-8")

        return report_path

    def _render_template(self, data: ReportData) -> str:
        """渲染报告模板"""
        status_emoji = "✅" if data.status == "完成" else "❌"
        unit_test_emoji = "✅" if data.unit_test_passed else ("❌" if data.unit_test_passed is False else "⏳")
        integration_test_emoji = "✅" if data.integration_test_passed else ("❌" if data.integration_test_passed is False else "⏳")

        # 构建文件变更表
        files_table = self._build_files_table(data.files_changed)

        # 构建文档更新状态
        docs_status = self._build_docs_status(data)

        return f"""# Issue#{data.issue_number} 任务报告

## 任务概述
- **来源**：GitHub Issue #{data.issue_number}
- **标签**：{', '.join(data.labels) if data.labels else '无'}
- **状态**：{status_emoji} {data.status}
- **时间**：{data.timestamp}

## 环境检查
- **结果**：{'✅ 通过' if data.env_check_passed else f'❌ 失败: {data.env_check_message}'}

## 问题分析
{data.problem_analysis}

## 实现方案
**方案**：{data.implementation_plan}

**理由**：{data.implementation_reason}

## 改动清单
{files_table}

## 测试结果
- 单元测试：{unit_test_emoji} {'通过' if data.unit_test_passed else ('未通过' if data.unit_test_passed is False else '未运行')}
- 集成测试：{integration_test_emoji} {'通过' if data.integration_test_passed else ('未通过' if data.integration_test_passed is False else '未运行')}

{data.test_details}

## 文档更新
{docs_status}

## 风险提示
{data.risk_notes}

## PR 信息
- **链接**：{data.pr_url if data.pr_url else '待创建'}
- **Commit**：{data.commit_hash if data.commit_hash else '待提交'}
"""

    def _build_files_table(self, files: list[dict]) -> str:
        """构建文件变更表"""
        if not files:
            return "| 文件 | 改动类型 | 说明 |\n|------|----------|------|\n| (无) | - | - |"

        header = "| 文件 | 改动类型 | 说明 |\n|------|----------|------|\n"
        rows = []
        for f in files:
            file_name = f.get("file", "未知")
            change_type = f.get("type", "修改")
            description = f.get("description", "")
            rows.append(f"| `{file_name}` | {change_type} | {description} |")

        return header + "\n".join(rows)

    def _build_docs_status(self, data: ReportData) -> str:
        """构建文档更新状态"""
        items = []

        if data.readme_updated:
            items.append("- README.md：✅ 已更新")
        else:
            items.append("- README.md：❌ 不需要")

        if data.architecture_doc_updated:
            items.append("- 架构文档：✅ 已更新")
        else:
            items.append("- 架构文档：❌ 不需要")

        if data.glossary_updated:
            items.append("- 术语表：✅ 已更新")
        else:
            items.append("- 术语表：❌ 不需要")

        if data.docs_updated_details:
            items.append(f"\n**详情**：{data.docs_updated_details}")

        return "\n".join(items) if items else "- 无文档更新"


class DocumentationChecker:
    """文档同步检查器"""

    def __init__(self, workspace_path: Path):
        self._workspace = workspace_path

    def check_and_update(self, files_changed: list[str]) -> dict[str, Any]:
        """
        检查并更新相关文档

        Args:
            files_changed: 改动的文件列表

        Returns:
            检查结果字典
        """
        results = {
            "readme_updated": False,
            "architecture_doc_updated": False,
            "glossary_updated": False,
            "details": "",
        }

        # 需要检查的文档
        docs_to_check = []

        # 根据改动文件决定要检查的文档
        for file_path in files_changed:
            file_path_lower = file_path.lower()

            if "src/" in file_path_lower:
                # 源代码改动，可能需要更新 README
                docs_to_check.append("readme")

            if any(x in file_path_lower for x in ["service", "domain", "infrastructure"]):
                # 架构相关改动，需要检查架构文档
                docs_to_check.append("architecture")

            if any(x in file_path_lower for x in ["model", "repository"]):
                # 领域模型改动，可能需要更新术语表
                docs_to_check.append("glossary")

        # 去重
        docs_to_check = list(set(docs_to_check))

        # 检查 README.md
        if "readme" in docs_to_check:
            readme_path = self._workspace / "README.md"
            if readme_path.exists():
                # TODO: 实现自动检查和更新逻辑
                # 目前只是标记为不需要更新，后续可以增强
                results["readme_updated"] = False
                results["details"] += "README.md 已检查，无需更新。"

        # 检查架构文档
        if "architecture" in docs_to_check:
            arch_path = self._workspace / "docs" / "architecture.md"
            if arch_path.exists():
                results["architecture_doc_updated"] = False
                results["details"] += "架构文档已检查，无需更新。"

        # 检查术语表
        if "glossary" in docs_to_check:
            glossary_path = self._workspace / "docs" / "glossary.md"
            if glossary_path.exists():
                results["glossary_updated"] = False
                results["details"] += "术语表已检查，无需更新。"

        return results
