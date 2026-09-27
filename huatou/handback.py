"""答完要不要把话头递回去（`docs/rules.md` §4）。

三道闸按从便宜到贵排，**抽签放最后**：没抽中就不消费随机数。理由是可复现性 ——
否则「这一轮被闸挡下」与「这一轮抽签没中」会混成同一个信号，注入同一个 rng 序列的
自检就分不清是哪一档在动。
"""
from __future__ import annotations

import re

from .dials import Dials
from .protocols import Rng
from .types import Channel, State, Verdict

__all__ = ["length_units", "should_hand_back"]


def length_units(msg: str) -> int:
    """他这一句去空白后有几个字。

    长度判据**只能有一份**：它有消费方两处 —— 放行的抽签，和评测报接话率时的分母。
    他只有「嗯」「还行」「就那样」这种回声的轮次，机制本来就不该递话头；
    把这些轮次算进分母，只会把实到率报低一档（实测 65% 对 71%）。评测里再写一遍
    判据，两边就会各漂各的。
    """
    return len(re.sub(r"\s+", "", str(msg or "")))


def should_hand_back(state: State, *, channel: "Channel | str", user_msg: str,
                     dials: Dials, rng: Rng) -> Verdict:
    """这一轮答完，要不要把话头递回去。

    抽中只是**允许**她递话头：他这句本身没什么可接的，她仍然可以不问 ——
    那个「纯寒暄逃逸口」目前只在 prompt 里，本库不假装能把它机械化。
    """
    if length_units(user_msg) < int(dials.hand_back_min_units(channel)):
        return Verdict.deny("too_short", "他这一句太短，没什么可接的")
    return Verdict.allow()