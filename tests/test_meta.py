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


def test_the_question_shapes_are_falsifiable(tmp_path):
    """去掉「句中吗」这一种形状（换成永不出现的字符），默认档必须红。

    真机那句「…坐了很久地铁吗，现在到哪了」只认这一档 —— 收口是「到哪了」，
    问号档与收口档都接不住它（`rules.md` §1 第 3 条）。
    """
    workspace = prepare(tmp_path, tests=["test_ask.py"])
    mutate(workspace, "huatou/ask.py",
           '_MA_ANYWHERE = "吗"\n',
           '_MA_ANYWHERE = "\\x00"\n')
    done = run_pytest(workspace, "tests/test_ask.py")
    assert done.returncode != 0, "少了一种问句形状，默认档居然没红"


def test_the_ask_streak_gate_is_falsifiable(tmp_path):
    """连问闸被旁路，默认档必须红 —— 她会变成一台追问机（§4 第 2 道）。"""
    workspace = prepare(tmp_path, tests=["test_handback.py"])
    mutate(workspace, "huatou/handback.py",
           "    if int(state.her_ask_streak or 0) >= int(dials.max_ask_streak):\n",
           "    if False:\n")
    done = run_pytest(workspace, "tests/test_handback.py")
    assert done.returncode != 0, "连问闸被旁路，默认档居然没红"


def test_the_empty_opener_list_is_falsifiable(tmp_path):
    """空转名单被清空（她又开始「你好」「在吗」），默认档必须红（§5 第 2 条）。"""
    workspace = prepare(tmp_path, tests=["test_lines.py"])
    mutate(workspace, "huatou/lines.py",
           "_EMPTY_OPENERS_PLAIN = frozenset(plain_text(x) for x in _EMPTY_OPENERS)\n",
           "_EMPTY_OPENERS_PLAIN = frozenset()\n")
    done = run_pytest(workspace, "tests/test_lines.py")
    assert done.returncode != 0, "名单被清空，默认档居然没红"


def test_the_dedup_window_is_falsifiable(tmp_path):
    """逐字重复那条判据失灵（永远说没重复），默认档必须红（§5 第 4 条）。"""
    workspace = prepare(tmp_path, tests=["test_lines.py"])
    mutate(workspace, "huatou/lines.py",
           "    window = int(dials.dedup_window or 0)\n",
           "    window = 0\n")
    done = run_pytest(workspace, "tests/test_lines.py")
    assert done.returncode != 0, "重复判据失灵，默认档居然没红"


def test_the_state_compatibility_is_falsifiable(tmp_path):
    """老状态的布尔量不再回落成「连问 1 轮」，默认档必须红（`rules.md` §6.4）。"""
    workspace = prepare(tmp_path, tests=["test_types.py"])
    mutate(workspace, "huatou/types.py",
           '        if not state.her_ask_streak and _as_bool(raw.get("last_her_ask"), False):\n'
           "            state.her_ask_streak = 1\n",
           "        if None:\n"
           "            state.her_ask_streak = 1\n")
    done = run_pytest(workspace, "tests/test_types.py")
    assert done.returncode != 0, "向前兼容断了，默认档居然没红"


def test_the_cheap_before_expensive_order_is_falsifiable(tmp_path):
    """内容闸被提前到前几道之前（白开一次库），默认档必须红（硬约束 4）。

    这条判据的落点是 `test_opening.py` 里那批 `probe.calls == 0`：
    前面任一道挡住时，探针一次都不许被调用。
    """
    workspace = prepare(tmp_path, tests=["test_opening.py"])
    mutate(workspace, "huatou/opening.py",
           "    if bool(state.waiting_user):\n",
           "    if bool(material.has_material()):\n"
           "        pass\n"
           "    if bool(state.waiting_user):\n")
    done = run_pytest(workspace, "tests/test_opening.py")
    assert done.returncode != 0, "探针被提前调用，默认档居然没红"


def test_the_arming_math_is_falsifiable(tmp_path):
    """`arm_after` 永远返回「不用等」，默认档必须红 —— 布防是她的待机入口。"""
    workspace = prepare(tmp_path, tests=["test_opening.py"])
    mutate(workspace, "huatou/opening.py",
           "    quiet_left = float(dials.open_sec(channel)) if quiet is None \\\n",
           "    return 0.0\n"
           "    quiet_left = float(dials.open_sec(channel)) if quiet is None \\\n")
    done = run_pytest(workspace, "tests/test_opening.py")
    assert done.returncode != 0, "布防时长被架空，默认档居然没红"


def test_the_privacy_guard_is_falsifiable(tmp_path):
    """把源产品的名字写回一个会被扫到的文件，隐私护栏必须红。

    名字在这里也是用码点拼的 —— 这份元档文件自己也不许带明文。
    """
    workspace = prepare(tmp_path, tests=["test_privacy.py"])
    name = "".join(chr(code) for code in (0x6797, 0x4E00, 0x6B23))
    (workspace / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    done = run_pytest(workspace, "tests/test_privacy.py")
    assert done.returncode != 0, "名字写回来了，隐私护栏居然没红"


def test_the_zero_dependency_guard_is_falsifiable(tmp_path):
    """包里混进一个第三方 import，零依赖护栏必须红（硬约束 1）。"""
    workspace = prepare(tmp_path, tests=["test_zero_deps.py"])
    mutate(workspace, "huatou/__init__.py",
           "from .dials import Dials\n",
           "import pytest\nfrom .dials import Dials\n")
    done = run_pytest(workspace, "tests/test_zero_deps.py")
    assert done.returncode != 0, "第三方 import 混进来了，护栏居然没红"
