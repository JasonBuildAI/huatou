"""门面：宿主拿到的那个对象。

判定只读状态，改写只有 `note_*` —— 两者混在一起的话，「这一次放不放行」与
「放行之后状态怎么变」就会有两处真源（硬约束 3）。

四个注入（材料探针、切句器、时钟、随机数）都存在公开属性上、**调用时现读**：
宿主换掉其中任何一个，下一次判定就跟着变，不需要重新构造。
"""
from __future__ import annotations

import random
import time

from . import ask, handback, lines, opening
from .dials import Dials
from .protocols import MaterialProbe
from .types import Channel, State, Verdict

__all__ = ["Floor"]


class Floor:
    """发言权。判定不改状态，`note_*` 才改状态。"""

    def __init__(self, *, dials: Dials, material: MaterialProbe,
                 split_sentences,
                 clock=time.time, rng=random.random,
                 banned_lines=()) -> None:
        self.dials = dials
        self.material = material
        self.split_sentences = split_sentences
        self.clock = clock
        self.rng = rng
        # 禁用句表：默认那三句 + 宿主加进来的（见 lines.banned_lines_with）。
        self.banned_lines = tuple(banned_lines or ())

    # ---------------------------------------------------------------- 判定
    def may_open(self, state: State, *, channel: "Channel | str") -> Verdict:
        """现在允不允许她主动开口。"""
        return opening.may_open(state, channel=channel, now=self.clock(),
                                dials=self.dials, material=self.material)

    def arm_after(self, state: State, *, channel: "Channel | str"):
        """还要安静多少秒才该布防；`None` = 不布防（终局或已关）。"""
        return opening.arm_after(state, channel=channel, now=self.clock(),
                                 dials=self.dials)

    def should_hand_back(self, state: State, *, channel: "Channel | str",
                         user_msg: str) -> Verdict:
        """这一轮答完，要不要把话头递回去。"""
        return handback.should_hand_back(state, channel=channel, user_msg=user_msg,
                                         dials=self.dials, rng=self.rng)

    def must_wait(self, state: State) -> bool:
        """她问过之后，是不是必须等用户真实开口。"""
        return bool(state.waiting_user)

    def line_rejected(self, state: State, line: str) -> str:
        """这一句能不能出口：返回理由串，空串 = 放行。"""
        return lines.line_rejected(state, line, dials=self.dials,
                                   split_sentences=self.split_sentences,
                                   banned_lines=self.banned_lines)

    def asks_the_user(self, text: str) -> bool:
        """她这一条是不是在**问他**（这一档判据的唯一实现）。"""
        return ask.asks_the_user(text)