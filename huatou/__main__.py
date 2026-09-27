"""`python -m huatou` 的入口：目前只有一个子命令 `demo`。

demo 跑的是仓库里的 `examples/companion.py` —— 一份假宿主的完整示范。
包被 pip 安装之后没有 `examples/` 目录，这时给一句人话，不抛 traceback：
「这条命令只在源码仓库里成立」与「包本身坏了」是两件事，要说得清。
"""
from __future__ import annotations

import pathlib
import runpy
import sys

__all__ = ["example_path", "main"]

_USAGE = "用法：python -m huatou demo —— 跑一遍假宿主的完整状态机"


def example_path() -> pathlib.Path:
    """示范脚本的位置：从包目录往上找 `examples/companion.py`。"""
    return pathlib.Path(__file__).resolve().parent.parent / "examples" / "companion.py"


def main(argv=None, *, path=None) -> int:
    """跑一个子命令，返回退出码。`path` 只为测试留一个口子。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["demo"]:
        print(_USAGE, file=sys.stderr)
        return 2
    target = pathlib.Path(path) if path is not None else example_path()
    if not target.is_file():
        print(f"找不到示范脚本：{target}\n"
              "它只在源码仓库里（examples/companion.py 那份文件）；"
              "pip 安装的包里没有它，包本身没问题。",
              file=sys.stderr)
        return 2
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as exc:                     # 示范脚本自己 sys.exit(0)
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
