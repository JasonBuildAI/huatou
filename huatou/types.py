"""公开的数据类型：口气档、判定结果、状态。

这个模块里**没有判据** —— 判据在 `ask.py` / `opening.py` / `handback.py` /
`lines.py` 里，它们都只读这里的数据结构。
"""
from __future__ import annotations

import math
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
    def to_dict(self) -> dict:
        """落盘 / 下发用的形状：只放 JSON 装得下的东西（硬约束 6）。

        `recent_said` 要**复制一份**：直接把它交出去，宿主那边一次 `append`
        就改到了活状态，判定与持久化的边界就没了。

        这里顺手把每个字段都过一遍类型（`or 0` / `str(x)`）：状态可能来自
        旧版本、也可能被人手改过，`to_dict` 是离开本库的最后一道口子，
        它吐出去的东西必须能被 JSON 序列化。
        """
        return {
            "streak": int(self.streak or 0),
            "last_open_ts": float(self.last_open_ts or 0.0),
            "text_fired": bool(self.text_fired),
            "waiting_user": bool(self.waiting_user),
            "her_ask_streak": int(self.her_ask_streak or 0),
            "recent_said": [str(x) for x in (self.recent_said or [])],
            "last_activity_ts": float(self.last_activity_ts or 0.0),
        }
    @classmethod
    def from_dict(cls, data) -> "State":
        """从落盘 / 下发的形状读回来（`docs/rules.md` §6.4）。

        失败姿态是**放宽，不是锁死**：认不出的键忽略、坏值取默认值、
        连形状都不对（不是字典）就整份取默认 —— 绝不抛给宿主。
        一个读不出来的字段让某个能力「永远卡住」，比读错一个数难查得多。
        """
        raw = data if isinstance(data, dict) else {}
        state = cls()
        state.streak = _as_int(_pick(raw, "streak"), 0)
        state.last_open_ts = _as_float(_pick(raw, "last_open_ts"), 0.0)
        state.text_fired = _as_bool(_pick(raw, "text_fired"), False)
        state.waiting_user = _as_bool(_pick(raw, "waiting_user"), False)
        state.her_ask_streak = _as_int(_pick(raw, "her_ask_streak"), 0)
        state.recent_said = _as_str_list(_pick(raw, "recent_said"))
        state.last_activity_ts = _as_float(_pick(raw, "last_activity_ts"), 0.0)
        # 向前兼容：老状态里只有一个布尔量 `last_her_ask`，读成「连问了 1 轮」。
        # 落回之后她照样能被允许再问一轮；读不出来的字段让能力永远卡住，
        # 正是这份状态机最不该有的失败姿态（`docs/rules.md` §6.4）。
        # 新字段在场时以新字段为准 —— 布尔量只是迁移期的替身。
        if not state.her_ask_streak and _as_bool(raw.get("last_her_ask"), False):
            state.her_ask_streak = 1
        return state
# 旧宿主的键名（迁移期替身）。宿主把老会话文件直接倒进 `State.from_dict` 也能跑，
# 不必自己写一层映射 —— 映射写错的症状是「她已经问过，她还在问」，很难查。
_LEGACY_KEYS = {
    "streak": "proactive_streak",
    "last_open_ts": "proactive_last_ts",
    "text_fired": "proactive_text_fired",
    "waiting_user": "proactive_waiting_user",
}


def _pick(raw: dict, key: str):
    """先读本库的键；缺席时退回旧宿主的键名，两个都没有就是 None。"""
    if raw.get(key) is not None:
        return raw[key]
    legacy = _LEGACY_KEYS.get(key)
    return raw.get(legacy) if legacy else None

def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default: float) -> float:
    """时间戳只认有限数：NaN / inf 会让每一次比较都静默变成 False。"""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _as_bool(value, default: bool) -> bool:
    """字符串按它的意思读：「false」「0」这类字面量不许被当成真。"""
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("", "0", "false", "no", "off", "none", "null"):
            return False
        return default
    if value is None:
        return default
    return bool(value)


def _as_str_list(value) -> list:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value]
    return []