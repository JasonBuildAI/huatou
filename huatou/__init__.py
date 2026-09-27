"""huatou（话头）—— 发言权管理器。

它只回答四个问题：现在允不允许她主动开口、这一轮答完要不要把话头递回去、
她问过之后是不是必须等他真实开口、这一句能不能出口。

它不生成内容、不合成、不播放、不检索，核心是纯标准库 ——
「有没有料」由宿主用 `MaterialProbe` 注入，时间与随机数由 `Clock` / `Rng` 注入。

判据逐条写在 `docs/rules.md`，边界与理由写在 `docs/design.md`。
"""
from .dials import Dials
from .floor import Floor
from .types import Channel, State, Verdict

__version__ = "0.1.0"

__all__ = ["Channel", "Dials", "Floor", "State", "Verdict", "__version__"]