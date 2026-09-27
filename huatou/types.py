"""公开的数据类型：口气档、判定结果、状态。

这个模块里**没有判据** —— 判据在 `ask.py` / `opening.py` / `handback.py` /
`lines.py` 里，它们都只读这里的数据结构。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = ["Channel", "State", "Verdict"]


class Channel(str, Enum):
    """口气档：文字 / 通话。两档的阈值不一样（见 `docs/rules.md` §3.2）。

    用 `str` 枚举是为了让宿主能直接拿它做字典键、写进 JSON、落进状态文件，
    不必再转一道。
    """

    TEXT = "text"
    CALL = "call"

    @classmethod
    def coerce(cls, value: "Channel | str") -> "Channel":
        """把宿主递进来的值收成枚举；认不出来的一律按文字档。

        文字档是**更保守**的那一档（安静阈值更长、长度闸更严），
        所以「看不懂就按文字档」与全库的失败姿态一致：宁可少说一句。
        """
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return cls.TEXT


@dataclass(frozen=True)
class Verdict:
    """一次判定的结果：放不放行 + 一个机器可读的理由 + 一句给人看的话。

    判定一律返回它，**不返回裸布尔**：面板上要能写出「她为什么没开口」，
    而不是让用户猜「她记性不太好 / 她怎么不理我」。理由串是稳定接口，
    改它等于改运维面板的一行字，要当成签名改动对待。
    """

    allowed: bool
    reason: str
    detail: str = ""

    @classmethod
    def allow(cls, reason: str = "ok", detail: str = "") -> "Verdict":
        return cls(True, reason, detail)

    @classmethod
    def deny(cls, reason: str, detail: str = "") -> "Verdict":
        return cls(False, reason, detail)

@dataclass
class State:
    """发言权的全部状态（`docs/rules.md` §6）。

    宿主持有它、也可以直接持久化它；**改写状态的入口只有 `Floor` 的 `note_*`**，
    判定函数一个字节都不写（硬约束 3）。字段默认值是「一个刚从没主动开过口的
    新会话」—— 于是老宿主不做迁移也能跑，行为是「她还没试过开口」。
    """

    # 连续主动开口了几次（用户一开口就清零）
    streak: int = 0
    # 上一次主动开口的时刻
    last_open_ts: float = 0.0
    # 文字端「这一回合已经主动挑过一次」
    text_fired: bool = False
    # 她问过一个带话头的问题，正在等用户真实回话
    waiting_user: bool = False
    # 她连着几轮都在问他（连问闸用）
    her_ask_streak: int = 0
    # 她最近说过的消息，最新在后（逐字重复判据的比对方）
    recent_said: list = field(default_factory=list)
    # 最后一次「谁说了话」的时刻（沉默判据的锚点；0 = 还没有活动记录）
    last_activity_ts: float = 0.0