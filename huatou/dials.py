"""阈值表：全部可调的数字只有这一张（硬约束 5）。

**调用时现读** —— 宿主随时可以换一份 `Dials`、或者改它的字段，下一次判定就跟着变。
不许在导入期把它快照成模块级常量：源系统在这上面踩过两次，症状一模一样 ——
猴补配置改不到它，而且**不报错**。

每一档的来源（实测 / 产品口径 / 拍的）逐条写在 `docs/rules.md` §3.2，
改数字之前先读那一栏。
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .types import Channel

__all__ = ["Dials"]


@dataclass
class Dials:
    """发言权的全部阈值。字段名与 `docs/rules.md` §3.2 的表一一对应。"""

    # 文字端 / 通话端安静多久算可以开口
    open_text_sec: float = 10.0
    open_call_sec: float = 4.0
    # 连续主动开口上限（0 = 关掉这个功能）
    max_streak: int = 2
    # 两次主动开口之间至少隔多少秒
    min_gap_sec: float = 8.0
    # 答完把话头递回去的抽签比例
    hand_back_ratio_text: float = 1.0
    hand_back_ratio_call: float = 0.95
    # 递话头的长度闸（去空白后的字数）
    hand_back_min_units_text: int = 4
    hand_back_min_units_call: int = 2
    # 连着几轮都问了就必停一轮
    max_ask_streak: int = 2
    # 逐字重复比对她最近几条消息
    dedup_window: int = 5

    def with_changes(self, **changes) -> "Dials":
        """改一两项、拿一份新的 —— 宿主不必知道 dataclass 的细节。"""
        return replace(self, **changes)

    def open_sec(self, channel: "Channel | str") -> float:
        """这一档要安静多久才算可以开口。"""
        return (self.open_call_sec if Channel.coerce(channel) is Channel.CALL
                else self.open_text_sec)

    def hand_back_ratio(self, channel: "Channel | str") -> float:
        """这一档答完递话头的抽签比例。"""
        return (self.hand_back_ratio_call if Channel.coerce(channel) is Channel.CALL
                else self.hand_back_ratio_text)

    def hand_back_min_units(self, channel: "Channel | str") -> int:
        """这一档的长度闸：去空白后不到这么多字就不抽。"""
        return (self.hand_back_min_units_call
                if Channel.coerce(channel) is Channel.CALL
                else self.hand_back_min_units_text)