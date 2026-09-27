"""出稿闸：这一句能不能出口（`docs/rules.md` §5）。

只判**主动开口的第一句**：后面几条是她展开的内容，拿黑名单去卡会把「你还好吗」
这种真的关心话误伤。真正的把关在内容闸（`opening.may_open` 的第七道），
这里只挡最能一眼看出没料的那一种。
"""
from __future__ import annotations

import re
from typing import Iterable

from .dials import Dials
from .types import State

__all__ = [
    "DEFAULT_BANNED_LINES",
    "banned_lines_with",
    "first_sentence",
    "line_rejected",
    "plain_text",
    "said_sentences",
]

# 空转黑名单（24 条纯问候 / 空开场）。判据是**整句相等**：「你好呀，今天画室特别安静……」
# 不算 —— 那是真的在说话。来历是反馈 6：用户原话是「不要频繁地说什么无意义的
# 『你好』『你好』」——一句「你好」把「她想起你了」变成了「她只会打招呼」。
_EMPTY_OPENERS = (
    "你好", "您好", "你好呀", "你好啊", "你好哇", "在吗", "你在吗", "在不在",
    "在么", "在嘛", "最近怎么样", "最近好吗", "你最近好吗", "你还好吗",
    "还好吗", "最近还好吗", "早上好", "早安", "哈喽", "hi", "hello",
    "在干嘛", "你在干嘛", "干嘛呢",
)



# 禁用句表。这三句在源系统里只写在 prompt 里：三层防线审计（prompt 说一遍 /
# 机器兜一道 / 度量看得见）里，它们的「机器」一格是空的 —— 也就是「模型高兴才算」。
# 本库把它补成第二层，并且允许宿主再加自己的句子。
DEFAULT_BANNED_LINES = (
    "你怎么不理我",
    "你怎么不回答我的问题",
    "你都不睬我",
)

def plain_text(text: str) -> str:
    """归一化成「只剩字」：标点、空白、表情符号全去掉，英文压成小写。

    逐字重复那条判据必须用它 ——「你好」与「你好！」「你好。」「你好～」是同一句话，
    不归一化的话，模型在尾巴上加个标点就绕过去了。
    """
    return re.sub(r"[\W_]+", "", str(text or "")).lower()
# 名单按归一化后的形状比对：模型在尾巴上加了标点也绕不过去。
_EMPTY_OPENERS_PLAIN = frozenset(plain_text(x) for x in _EMPTY_OPENERS)


def first_sentence(split_sentences, line: str) -> str:
    """她这一句的**第一句** —— 出稿闸只判它。

    后面几条是她展开的内容，拿黑名单去卡会把「你还好吗」这种真的关心话误伤。
    切句器抛出异常、或者切不出东西时退回整条：闸门不因为工具坏了就把话吃掉。
    """
    text = str(line or "")
    try:
        parts = [str(s).strip() for s in split_sentences(text)]
    except Exception:                             # noqa: BLE001
        parts = []
    parts = [part for part in parts if part]
    return parts[0] if parts else text.strip()


def said_sentences(split_sentences, text) -> list:
    """她某一条消息里**说过的每一句**（逐字重复那条判据的比对方）。"""
    try:
        parts = [str(s).strip() for s in split_sentences(str(text or ""))]
    except Exception:                             # noqa: BLE001
        return []
    return [part for part in parts if part]


def repeats_recent(state: State, plain: str, *, dials: Dials,
                   split_sentences) -> bool:
    """这一句是不是她最近说过的某一句（比她最近 `dedup_window` 条消息）。"""
    window = int(dials.dedup_window or 0)
    if window <= 0:
        return False
    recent = list(state.recent_said or [])[-window:]
    for message in recent:
        for sentence in said_sentences(split_sentences, message):
            if plain_text(sentence) == plain:
                return True
    return False


def banned_lines_with(extra: Iterable[str] = ()) -> tuple:
    """默认禁用句 + 宿主自己加的，去重后返回（顺序稳定，便于日志比对）。"""
    out = list(DEFAULT_BANNED_LINES)
    seen = set(out)
    for item in extra or ():
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


def is_banned_line(line: str, banned_lines: Iterable[str]) -> bool:
    """这一句是不是禁用句。两档：先原样相等，再归一化后相等。

    归一化那一档是兜底：尾巴上加个标点、多空几格（「你怎么不理我。」）不该绕过去。
    两档都会判，任一中就是命中 —— 分成两档是为了让加进来的句子既有「原话相等」
    这条最直观的判据，也不至于被一个标点绕过去。
    """
    text = str(line or "").strip()
    plain = plain_text(text)
    for entry in banned_lines or ():
        if text == str(entry or "").strip():
            return True
        if plain and plain == plain_text(entry):
            return True
    return False


def line_rejected(state: State, line: str, *, dials: Dials, split_sentences,
                  banned_lines: Iterable[str] = ()) -> str:
    """这一句能不能出口：返回**理由串**，空串 = 放行。

    回理由而不是布尔，与 `Verdict` 是同一个理由：面板上要能写出「她为什么说不出话」。
    顺序按从便宜到贵：不是话 → 空转名单 → 禁用句 → 逐字重复。

    禁用句那条也**只判第一句**：她开口先说「你怎么不理我」、后面再补一句家常，
    读起来仍然是那三句里的一句在指责他，不能因为后半句让她溜过去。
    切句器坏了时 `first_sentence` 退回整条，这条判据跟着退回整条 —— 失败姿态是收紧。
    """
    first = first_sentence(split_sentences, line)
    plain = plain_text(first)
    if not plain:
        return "not_a_line"      # 纯标点 / 表情：不是话
    if is_banned_line(first, banned_lines_with(banned_lines)):
        return "banned_line"
    if plain in _EMPTY_OPENERS_PLAIN:
        # 整句相等才挡：「你好呀，今天画室特别安静……」不算，那是真的在说话。
        return "empty_opener"
    if repeats_recent(state, plain, dials=dials, split_sentences=split_sentences):
        # 逐字重复**按句比，不按条比**：历史里一条消息常常是好几句，而这里收到的
        # 是切句之后的一句。两边必须过同一个切句器 —— 注入而不是内置，
        # 是为了让「两边同源」这件事在类型上就成立。
        return "repeat"
    return ""