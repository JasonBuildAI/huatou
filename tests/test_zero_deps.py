"""硬约束 1：核心零第三方依赖（`docs/design.md` §6 第 1 条）。

`import huatou` 之后，`sys.modules` 里不许出现任何非标准库模块。理由：本库要在
宿主的进程里被 import，而宿主可能装了几百个包 —— 本库一旦悄悄依赖某个第三方库，
宿主升级它就会把我们带崩，而症状离原因很远（「她怎么不开口了」）。

判据必须在**干净的进程**里跑：本进程早就 import 过 pytest 之类的东西；
而且要拿 import 前后的差集，不能用「现在 sys.modules 里有什么」——
解释器启动时就已经加载的模块（比如 setuptools 的 `_distutils_hack`）与本库无关。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_PROBE = """
import json, sys

before = set(sys.modules)
import huatou

after = set(sys.modules) - before
stdlib = set(sys.stdlib_module_names)
extra = sorted(n for n in after
               if n.split(".")[0] not in stdlib and not n.startswith("huatou"))
print(json.dumps(extra))
"""


def test_importing_huatou_pulls_in_no_third_party_module():
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == []