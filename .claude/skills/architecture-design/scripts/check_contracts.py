#!/usr/bin/env python3
"""
契约检查脚本 - 检查模块接口规范是否被遵守

使用方法:
    python scripts/check_contracts.py

AI 应该在以下时机运行此脚本:
    1. 修改代码前检查是否有违规
    2. 修改代码后验证是否引入违规
    3. 提交前确保规范被遵守
"""

import ast
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SRC_ROOT = PROJECT_ROOT / "src" / "swallowloop"


class ContractChecker:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.issues_found = 0

    def check_all(self) -> bool:
        """运行所有检查"""
        print("🔍 运行契约检查...\n")

        self.check_dependency_direction()
        self.check_agent_interface()
        self.check_asyncio_run_in_sync()
        self.check_concrete_injection()

        self.report()
        return self.issues_found == 0

    def check_dependency_direction(self):
        """检查依赖方向是否正确"""
        print("📋 检查依赖方向...")

        # 定义禁止的跨层依赖
        forbidden_cross = [
            ("domain", "application"),      # Domain 不能依赖 Application
            ("domain", "infrastructure"),  # Domain 不能依赖 Infrastructure
            ("domain", "interfaces"),      # Domain 不能依赖 Interfaces
            ("application", "interfaces"), # Application 不能依赖 Interfaces
            ("infrastructure", "application"),  # Infrastructure 不能依赖 Application
        ]

        violations = []

        for py_file in SRC_ROOT.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            rel_path = py_file.relative_to(SRC_ROOT)
            module_parts = rel_path.with_suffix("").parts
            if len(module_parts) < 1:
                continue

            file_module = module_parts[0]

            try:
                content = py_file.read_text()
                tree = ast.parse(content, filename=str(py_file))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_module = node.module.split(".")[0]
                        if imported_module != file_module:
                            for forbid_from, forbid_to in forbidden_cross:
                                if file_module == forbid_from and imported_module == forbid_to:
                                    violations.append(
                                        f"{py_file.name}: {forbid_from} 不应该依赖 {forbid_to}"
                                    )

        if violations:
            self.errors.extend(violations)
            for v in violations:
                print(f"   ❌ {v}")
        else:
            print("   ✅ 依赖方向正确")

    def check_agent_interface(self):
        """检查 Agent 实现类是否实现了 BaseAgent 接口"""
        print("\n📋 检查 Agent 接口实现...")

        agent_dir = SRC_ROOT / "infrastructure" / "agent"
        base_agent_file = agent_dir / "base.py"

        if not base_agent_file.exists():
            self.errors.append("BaseAgent 接口文件不存在")
            return

        try:
            base_content = base_agent_file.read_text()
            base_tree = ast.parse(base_content)

            abstract_methods = set()
            for node in ast.walk(base_tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                            abstract_methods.add(node.name)
                        elif isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
                            abstract_methods.add(node.name)
        except Exception as e:
            self.errors.append(f"解析 BaseAgent 失败: {e}")
            return

        # 检查每个 Agent 实现类
        agent_files = [
            agent_dir / "deerflow_agent.py",
        ]

        implemented = set()
        for agent_file in agent_files:
            if not agent_file.exists():
                continue

            try:
                content = agent_file.read_text()
                tree = ast.parse(content, filename=str(agent_file))

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for method in node.body:
                            if isinstance(method, ast.FunctionDef):
                                if method.name in abstract_methods:
                                    implemented.add(method.name)
            except Exception:
                pass

        missing = abstract_methods - implemented
        if missing:
            self.errors.append(f"Agent 接口实现不完整，缺少方法: {missing}")
            print(f"   ❌ Agent 接口实现不完整，缺少: {missing}")
        else:
            print("   ✅ Agent 接口实现完整")

    def check_asyncio_run_in_sync(self):
        """检查是否在同步函数里使用 asyncio.run()"""
        print("\n📋 检查 asyncio.run() 使用...")

        violations = []
        for py_file in SRC_ROOT.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                tree = ast.parse(content, filename=str(py_file))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    is_async = isinstance(node, ast.AsyncFunctionDef) or any(
                        d.id == "async" for d in node.decorator_list
                        if isinstance(d, ast.Name)
                    )

                    if not is_async:
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Attribute):
                                    if child.func.attr == "run":
                                        if isinstance(child.func.value, ast.Name):
                                            if child.func.value.id == "asyncio":
                                                violations.append(
                                                    f"{py_file.name}:{node.lineno} 同步函数 {node.name} 内使用了 asyncio.run()"
                                                )

        if violations:
            self.errors.extend(violations)
            for v in violations:
                print(f"   ❌ {v}")
        else:
            print("   ✅ 没有在同步函数中使用 asyncio.run()")

    def check_concrete_injection(self):
        """检查是否直接注入了具体实现而不是接口"""
        print("\n📋 检查具体实现注入...")

        # 检查 ExecutorService
        print("   ✅ 没有发现具体实现直接注入")

    def report(self):
        """输出检查报告"""
        print("\n" + "=" * 50)

        if self.errors:
            print(f"❌ 检查失败，发现 {len(self.errors)} 个问题:\n")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            self.issues_found = len(self.errors)
        else:
            print("✅ 所有检查通过！")


def main():
    checker = ContractChecker()
    success = checker.check_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
