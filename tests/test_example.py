"""示范脚本的冒烟：它是一份会跑的文档，必须真的跑得完。

它同时验两条路：`python examples/companion.py`（直接跑文件，
sys.path[0] 是 examples/）与任意工作目录下的同一条命令 —— 脚本自己把仓库根
补进 sys.path，所以两条路都得通。`python -m huatou demo` 那条入口另有一份测试。
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "examples" / "companion.py"


def run_example(cwd):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=str(cwd),
                          capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=60)


def test_the_example_runs_from_the_repo_root():
    done = run_example(ROOT)
    assert done.returncode == 0, done.stderr
    assert "状态机跑完一遍" in done.stdout


def test_the_example_runs_from_any_working_directory(tmp_path):
    """从别的目录跑也不缺 import —— 示范脚本不该假设自己在仓库根被启动。"""
    done = run_example(tmp_path)
    assert done.returncode == 0, done.stderr
    assert "状态机跑完一遍" in done.stdout
