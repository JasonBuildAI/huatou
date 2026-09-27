"""`python -m huatou demo`：包自带入口，不依赖读的人猜到 examples/ 在哪。

子进程那条验的是**真命令**（design.md §8 的第三条验收），
进程内那几条验的是它的三种失败姿态：没给对子命令、包里没有示范文件。
"""
import os
import pathlib
import subprocess
import sys

from huatou.__main__ import example_path, main

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_demo_command_runs_end_to_end():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    done = subprocess.run([sys.executable, "-m", "huatou", "demo"], cwd=str(ROOT),
                          capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=60)
    assert done.returncode == 0, done.stderr
    assert "状态机跑完一遍" in done.stdout


def test_the_demo_entry_runs_the_shipped_example(capsys):
    """进程内跑一遍：入口返回 0，示范的输出确实走的是这份脚本。"""
    assert example_path() == ROOT / "examples" / "companion.py"
    assert main(["demo"]) == 0
    assert "布防" in capsys.readouterr().out


def test_no_subcommand_prints_usage_and_returns_two(capsys):
    assert main([]) == 2
    assert "python -m huatou demo" in capsys.readouterr().err
    assert main(["run"]) == 2


def test_a_package_without_the_example_says_so(capsys, tmp_path):
    """pip 安装的包里没有 examples/：说清是哪一件事缺了，不抛 traceback。"""
    missing = tmp_path / "examples" / "companion.py"
    assert main(["demo"], path=missing) == 2
    err = capsys.readouterr().err
    assert "找不到示范脚本" in err and "源码仓库" in err
