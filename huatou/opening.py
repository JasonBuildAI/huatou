"""主动开口：现在允不允许她开口，以及还要安静多久才该布防。

两件事分开回答（`docs/rules.md` §3.1）：`may_open` 是**放行**，
`arm_after` 是**布防**。布防侧知道「安静了多久」这件事在宿主手里，
但沉默阈值只有一份，所以两个函数都从这里读同一张 `Dials`。

判定是纯函数：时间由宿主递进来（`now`），函数体里不取时钟 ——
这样「安静 9.9 秒不放行、10.1 秒放行」可以用假时钟精确钉死。
"""
from __future__ import annotations

from .dials import Dials
from .protocols import MaterialProbe
from .types import Channel, State, Verdict

__all__ = ["may_open"]


def may_open(state: State, *, channel: "Channel | str", now: float,
             dials: Dials, material: MaterialProbe) -> Verdict:
    """现在允不允许她主动开口。

    判据按**从便宜到贵**排，最贵的那道要读库、必须最后一个跑（硬约束 4）：
    否则每一个不放行的轮次都要白开一次库。任何一条不满足都返回带理由的
    `Verdict`，不返回裸布尔。判定只读 `state`。
    """
    if int(dials.max_streak or 0) <= 0:
        return Verdict.deny("disabled", "这个功能是关掉的：max_streak = 0")
    return Verdict.allow()