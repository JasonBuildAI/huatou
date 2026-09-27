"""公开的数据类型：口气档、判定结果、状态。

这个模块里**没有判据** —— 判据在 `ask.py` / `opening.py` / `handback.py` /
`lines.py` 里，它们都只读这里的数据结构。
"""
from __future__ import annotations

from enum import Enum

__all__ = ["Channel"]


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