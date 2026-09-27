"""骨架冒烟：包能被 pytest 收到、能被导入、版本号在。

这一条最早存在，是为了让「一条用例都没收到」（pytest 退出码 5）以失败之外的
形式暴露出来：从第一个可跑的状态起，`python -m pytest` 就得是有意义的。
"""
from pathlib import Path

import huatou


def test_package_exposes_a_version():
    assert huatou.__version__


def test_imports_the_working_copy_not_an_installed_copy():
    """测试跑的必须是工作区这一份 —— 否则改代码不生效，红绿都是假的。"""
    here = Path(__file__).resolve().parent.parent / "huatou"
    assert Path(huatou.__file__).resolve().parent == here

def test_the_facade_exports_the_five_public_names():
    """`import huatou` 之后的五个门面名字 —— 宿主只认它们。"""
    import huatou
    from huatou.dials import Dials
    from huatou.floor import Floor
    from huatou.types import Channel, State, Verdict

    assert huatou.Floor is Floor
    assert huatou.Dials is Dials
    assert huatou.Channel is Channel
    assert huatou.State is State
    assert huatou.Verdict is Verdict
    assert set(huatou.__all__) == {"Channel", "Dials", "Floor", "State",
                                   "Verdict", "__version__"}