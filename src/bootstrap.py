"""
Hunter AI 内容工厂 - 环境自检与自动安装模块

功能：
- 检测操作系统类型（Windows/macOS/Linux）
- 检查 Python 版本（需要 3.12+）
- 检查 UV 包管理器
- 自动安装缺失的依赖
- 检查 config.yaml 配置文件

使用方法：
    python -m src.bootstrap          # 运行环境检查
    python -m src.bootstrap --fix    # 自动修复环境问题

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# 颜色输出（跨平台兼容）
class Colors:
    """终端颜色输出"""

    # Windows 需要启用 ANSI 支持
    if platform.system() == "Windows":
        os.system("")  # 启用 Windows ANSI 支持

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def error(cls, msg: str) -> str:
        return f"{cls.RED}❌ {msg}{cls.RESET}"

    @classmethod
    def success(cls, msg: str) -> str:
        return f"{cls.GREEN}✅ {msg}{cls.RESET}"

    @classmethod
    def warning(cls, msg: str) -> str:
        return f"{cls.YELLOW}⚠️  {msg}{cls.RESET}"

    @classmethod
    def info(cls, msg: str) -> str:
        return f"{cls.CYAN}ℹ️  {msg}{cls.RESET}"

    @classmethod
    def header(cls, msg: str) -> str:
        return f"{cls.BOLD}{cls.CYAN}{msg}{cls.RESET}"


class EnvironmentChecker:
    """环境检查器"""

    # 最低 Python 版本要求
    MIN_PYTHON_VERSION = (3, 12)

    # 项目根目录
    ROOT_DIR = Path(__file__).parent.parent

    def __init__(self):
        """初始化检查器"""
        self.os_type = platform.system()  # Windows, Darwin, Linux
        self.os_name = self._get_os_name()
        self.issues = []  # 收集问题
        self.fixes_applied = []  # 已应用的修复
        self.validation_errors = []  # 配置验证错误详情

    def _get_os_name(self) -> str:
        """获取友好的操作系统名称"""
        os_map = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Ubuntu/Linux"}
        return os_map.get(self.os_type, self.os_type)

    def print_header(self):
        """打印检查头部"""
        print(
            Colors.header(f"""
╔════════════════════════════════════════════╗
║     🦅 Hunter AI 环境自检工具 v2.0         ║
╠════════════════════════════════════════════╣
║  操作系统: {self.os_name:<30} ║
╚════════════════════════════════════════════╝
""")
        )

    def check_python_version(self) -> tuple[bool, str]:
        """检查 Python 版本"""
        current = sys.version_info[:2]
        required = self.MIN_PYTHON_VERSION

        if current >= required:
            return True, f"Python {current[0]}.{current[1]}"
        else:
            self.issues.append("python_version")
            return False, f"Python {current[0]}.{current[1]} (需要 {required[0]}.{required[1]}+)"

    def check_uv_installed(self) -> tuple[bool, str]:
        """检查 UV 是否安装"""
        uv_path = shutil.which("uv")

        if uv_path:
            # 获取版本
            try:
                result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=10)
                version = result.stdout.strip().split()[-1] if result.returncode == 0 else "未知"
                return True, f"UV {version}"
            except Exception:
                return True, "UV 已安装"
        else:
            self.issues.append("uv_missing")
            return False, "UV 未安装"

    def check_config_file(self) -> tuple[bool, str]:
        """检查 config.yaml 配置文件"""
        import yaml

        config_file = self.ROOT_DIR / "config.yaml"
        self.ROOT_DIR / "config.example.yaml"

        if config_file.exists():
            # 检查关键配置是否填写
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}

                # 检查必填项
                missing = []
                gemini_key = config.get("gemini", {}).get("api_key", "")
                if not gemini_key or gemini_key == "your_gemini_api_key_here":
                    missing.append("gemini.api_key")

                if missing:
                    self.issues.append("config_incomplete")
                    return False, f"config.yaml 存在但未配置: {', '.join(missing)}"

                return True, "config.yaml 已配置"
            except Exception as e:
                self.issues.append("config_invalid")
                return False, f"config.yaml 格式错误: {e}"
        else:
            self.issues.append("config_missing")
            return False, "config.yaml 文件不存在"

    def check_config_validation(self) -> tuple[bool, str]:
        """使用 ConfigValidator 进行深度配置验证"""
        config_file = self.ROOT_DIR / "config.yaml"

        if not config_file.exists():
            # config_file 检查会处理这个情况
            return True, "跳过（配置文件不存在）"

        try:
            # 导入配置验证器
            from src.utils.config_validator import ConfigValidator

            validator = ConfigValidator(config_file)
            result = validator.validate()

            if result.passed:
                warning_count = len(result.warnings)
                if warning_count > 0:
                    return True, f"验证通过（{warning_count} 个警告）"
                return True, "验证通过"
            else:
                error_count = len(result.errors)
                self.issues.append("config_validation_failed")
                # 记录详细错误供后续使用
                self.validation_errors = result.errors
                return False, f"验证失败（{error_count} 个错误）"

        except ImportError:
            # 如果依赖未安装，跳过此检查
            return True, "跳过（依赖未安装）"
        except Exception as e:
            return True, f"跳过（{e}）"

    def check_dependencies(self) -> tuple[bool, str]:
        """检查依赖是否安装"""
        venv_dir = self.ROOT_DIR / ".venv"

        if venv_dir.exists():
            return True, "依赖已安装 (.venv)"
        else:
            self.issues.append("deps_missing")
            return False, "依赖未安装"

    def check_directories(self) -> tuple[bool, str]:
        """检查必要目录"""
        required_dirs = ["data", "output"]
        missing = []

        for dir_name in required_dirs:
            dir_path = self.ROOT_DIR / dir_name
            if not dir_path.exists():
                missing.append(dir_name)

        if missing:
            self.issues.append("dirs_missing")
            return False, f"缺少目录: {', '.join(missing)}"

        return True, "目录结构完整"

    def run_checks(self) -> bool:
        """运行所有检查"""
        self.print_header()

        checks = [
            ("Python 版本", self.check_python_version),
            ("UV 包管理器", self.check_uv_installed),
            ("依赖安装", self.check_dependencies),
            ("配置文件", self.check_config_file),
            ("配置验证", self.check_config_validation),
            ("目录结构", self.check_directories),
        ]

        print(Colors.header("📋 环境检查结果：\n"))

        all_passed = True
        for name, check_func in checks:
            passed, detail = check_func()
            status = Colors.success(detail) if passed else Colors.error(detail)
            print(f"  {name:<15} {status}")
            if not passed:
                all_passed = False

        # 如果有配置验证错误，打印详情
        if self.validation_errors:
            print(Colors.header("\n📝 配置验证错误详情："))
            for error in self.validation_errors:
                print(f"  • {error}")

        print()
        return all_passed

    def install_uv(self) -> bool:
        """安装 UV"""
        print(Colors.info("正在安装 UV..."))

        try:
            if self.os_type == "Windows":
                # Windows 使用 PowerShell
                cmd = 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
            else:
                # macOS / Linux 使用 curl
                cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                print(Colors.success("UV 安装成功"))
                self.fixes_applied.append("UV 安装")
                return True
            else:
                print(Colors.error(f"UV 安装失败: {result.stderr}"))
                return False
        except Exception as e:
            print(Colors.error(f"UV 安装异常: {e}"))
            return False

    def install_dependencies(self) -> bool:
        """安装项目依赖"""
        print(Colors.info("正在安装依赖..."))

        try:
            result = subprocess.run(["uv", "sync"], cwd=self.ROOT_DIR, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(Colors.success("依赖安装成功"))
                self.fixes_applied.append("依赖安装")
                return True
            else:
                print(Colors.error(f"依赖安装失败: {result.stderr}"))
                return False
        except Exception as e:
            print(Colors.error(f"依赖安装异常: {e}"))
            return False

    def create_config_file(self) -> bool:
        """从模板创建 config.yaml 文件"""
        config_file = self.ROOT_DIR / "config.yaml"
        config_example = self.ROOT_DIR / "config.example.yaml"

        if not config_example.exists():
            print(Colors.error("config.example.yaml 模板不存在"))
            return False

        try:
            shutil.copy(config_example, config_file)
            print(Colors.success("config.yaml 文件已创建"))
            print(Colors.warning("请编辑 config.yaml 文件填写 API Key"))
            self.fixes_applied.append("config.yaml 创建")
            return True
        except Exception as e:
            print(Colors.error(f"创建 config.yaml 失败: {e}"))
            return False

    def create_directories(self) -> bool:
        """创建必要目录"""
        required_dirs = ["data", "output"]

        try:
            for dir_name in required_dirs:
                dir_path = self.ROOT_DIR / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)

            print(Colors.success("目录创建成功"))
            self.fixes_applied.append("目录创建")
            return True
        except Exception as e:
            print(Colors.error(f"创建目录失败: {e}"))
            return False

    def auto_fix(self) -> bool:
        """自动修复环境问题"""
        if not self.issues:
            print(Colors.success("环境检查通过，无需修复"))
            return True

        print(Colors.header("\n🔧 开始自动修复环境...\n"))

        # 修复顺序很重要
        fix_map = {
            "python_version": (None, "请手动安装 Python 3.12+"),
            "uv_missing": (self.install_uv, None),
            "deps_missing": (self.install_dependencies, None),
            "config_missing": (self.create_config_file, None),
            "config_incomplete": (None, "请编辑 config.yaml 文件填写配置"),
            "config_invalid": (None, "请检查 config.yaml 文件格式是否正确"),
            "config_validation_failed": (None, "请运行 `uv run hunter validate` 查看详细错误"),
            "dirs_missing": (self.create_directories, None),
        }

        all_fixed = True
        for issue in self.issues:
            fix_func, manual_msg = fix_map.get(issue, (None, None))

            if fix_func:
                if not fix_func():
                    all_fixed = False
            elif manual_msg:
                print(Colors.warning(manual_msg))
                all_fixed = False

        if self.fixes_applied:
            print(Colors.header(f"\n✨ 已应用修复: {', '.join(self.fixes_applied)}"))

        return all_fixed


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Hunter AI 环境自检工具")
    parser.add_argument("--fix", action="store_true", help="自动修复环境问题")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式（仅输出错误）")
    args = parser.parse_args()

    checker = EnvironmentChecker()

    # 运行检查
    all_passed = checker.run_checks()

    if all_passed:
        print(Colors.success("环境检查全部通过！可以启动 Hunter AI\n"))
        return 0

    # 有问题，尝试修复
    if args.fix:
        if checker.auto_fix():
            print(Colors.success("\n环境修复完成！请重新运行检查\n"))
            return 0
        else:
            print(Colors.warning("\n部分问题需要手动修复\n"))
            return 1
    else:
        print(Colors.warning("运行 `python -m src.bootstrap --fix` 尝试自动修复\n"))
        return 1


if __name__ == "__main__":
    sys.exit(main())
