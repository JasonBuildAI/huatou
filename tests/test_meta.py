"""元档：证明每条判据都能红（`design.md` §8、`rules.md` §7 第 11 条）。

这一档不测 huatou 的行为，测的是**默认档的警觉度**：把实现改坏一点，
子进程里的默认档必须变红。做法是把 `huatou/` 与相关测试复制到临时目录，
在副本上做一处变异，再起一个真的 pytest 子进程 ——
「评测与实现同源就等于没有评测」，所以这里连跑测试的进程都要是新的。

默认档不选它（`pyproject.toml` 的 `-m "not meta"`）；`python -m pytest -m meta`
才跑。子进程一律显式带上那两个 `-p no:`，因为临时目录里没有这份配置。
"""
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.meta


def child_env():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    return env


def run_pytest(where, *args):
    """起一个真 pytest 子进程；返回 CompletedProcess（stdout/stderr 都是文本）。"""
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "-p", "no:hydra_pytest", "-p", "no:langsmith_plugin", *args]
    return subprocess.run(cmd, cwd=str(where), capture_output=True, text=True,
                          encoding="utf-8", env=child_env(), timeout=180)


def prepare(tmp_path, tests=()):
    """把包与指定的测试文件复制进临时目录，返回那个目录。

    子进程的 cwd 就是这里，`python -m pytest` 会把 cwd 放进 sys.path 最前 ——
    所以子进程 import 到的是**副本**，变异不会碰到真源码。
    """
    workspace = tmp_path / "workspace"
    shutil.copytree(ROOT / "huatou", workspace / "huatou")
    (workspace / "tests").mkdir()
    for name in tests:
        shutil.copy(ROOT / "tests" / name, workspace / "tests" / name)
    return workspace


def mutate(workspace, relative, old, new):
    """把副本里的一处源码改坏；锚点找不到就直接失败（防锚点腐烂）。"""
    path = workspace / relative
    text = path.read_text(encoding="utf-8")
    assert old in text, f"锚点不在 {relative} 里：{old[:60]!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def test_the_child_pytest_really_reports_red(tmp_path):
    """先证明这套装置不是恒绿：一份注定失败的用例，子进程必须报红。"""
    workspace = prepare(tmp_path)
    (workspace / "tests" / "test_always_red.py").write_text(
        "def test_red():\n    assert False, '这份用例就是该红的'\n", encoding="utf-8")
    done = run_pytest(workspace, "tests/test_always_red.py")
    assert done.returncode != 0
    assert "1 failed" in done.stdout


def test_the_default_gate_does_not_collect_the_meta_tier():
    """默认档不选元档；`-m meta` 才收集它 —— 两句话都要真的成立。"""
    default = run_pytest(ROOT, "--collect-only", "tests/test_meta.py")
    assert "test_meta.py::" not in default.stdout, default.stdout[-400:]
    meta = run_pytest(ROOT, "-m", "meta", "--collect-only", "tests/test_meta.py")
    assert "test_meta.py::" in meta.stdout, meta.stdout[-400:]


def test_the_waiting_user_gate_is_falsifiable(tmp_path):
    """关掉「她问过就等他回话」这一道，默认档必须红（§2 第 2 道）。"""
    workspace = prepare(tmp_path, tests=["test_opening.py"])
    mutate(workspace, "huatou/opening.py",
           '    if bool(state.waiting_user):\n'
           '        return Verdict.deny("waiting_user", "她问过，还没等到他真实开口")\n',
           '    if False:\n'
           '        return Verdict.deny("waiting_user", "她问过，还没等到他真实开口")\n')
    done = run_pytest(workspace, "tests/test_opening.py")
    assert done.returncode != 0, "关掉这一道闸，默认档居然没红"


def test_the_material_gate_is_falsifiable(tmp_path):
    """内容闸恒真（等于不查库），默认档必须红 —— 没料就不开口（§2 第 7 道）。"""
    workspace = prepare(tmp_path, tests=["test_opening.py"])
    mutate(workspace, "huatou/opening.py",
           "        material_ready = bool(material.has_material())\n",
           "        material_ready = True\n")
    done = run_pytest(workspace, "tests/test_opening.py")
    assert done.returncode != 0, "内容闸被架空了，默认档居然没红"
