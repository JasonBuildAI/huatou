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

__all__ = ["may_open", "quiet_sec"]


def quiet_sec(state: State, now: float) -> "float | None":
    """从最后一次活动到现在安静了多久；还没有活动记录时返回 None。

    None 的意思是「这件事归布防侧管」：一个新会话在页面打开之前没有任何活动时间，
    服务端不假装知道它已经安静了多久（`docs/rules.md` §3.1）。
    一旦宿主记过活动时间（任何一个 `note_*` 都会记），这一档就是服务端的兜底。
    """
    ts = float(state.last_activity_ts or 0.0)
    if ts <= 0.0:
        return None
    return max(0.0, float(now) - ts)


def may_open(state: State, *, channel: "Channel | str", now: float,
             dials: Dials, material: MaterialProbe) -> Verdict:
    """现在允不允许她主动开口。

    判据按**从便宜到贵**排，最贵的那道要读库、必须最后一个跑（硬约束 4）：
    否则每一个不放行的轮次都要白开一次库。任何一条不满足都返回带理由的
    `Verdict`，不返回裸布尔。判定只读 `state`。
    """
    if int(dials.max_streak or 0) <= 0:
        return Verdict.deny("disabled", "这个功能是关掉的：max_streak = 0")
    if bool(state.waiting_user):
        return Verdict.deny("waiting_user", "她问过，还没等到他真实开口")
    if Channel.coerce(channel) is Channel.TEXT and bool(state.text_fired):
        return Verdict.deny("text_fired", "文字端这一回合已经主动挑过一次")
    if int(state.streak or 0) >= int(dials.max_streak):
        return Verdict.deny("max_streak", "试过了，等他开口（终局语义）")
    quiet = quiet_sec(state, now)
    if quiet is not None and quiet < float(dials.open_sec(channel)):
        return Verdict.deny("quiet", "还安静得不够：再等等")
    if float(now) - float(state.last_open_ts or 0.0) < float(dials.min_gap_sec):
        return Verdict.deny("min_gap", "距上一次主动开口还不够久")
    if float(now) - float(state.last_open_ts or 0.0) < float(dials.min_gap_sec):
        return Verdict.deny("min_gap", "距上一次主动开口还不够久")
    # 内容闸：唯一要读库的一道，所以必须最后一个跑（硬约束 4）。手里一点素材都
    # 没有时她「起个头」只能靠编，而用户读到的就是「她说的话跟我完全无关」——
    # 没料就不开口，比硬找一句话说不强。
    if not bool(material.has_material()):
        return Verdict.deny("no_material", "手里一点素材都没有：这次不开口，等他先说")
    return Verdict.allow()