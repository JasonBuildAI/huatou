"""「她有没有在问他」—— 这一档判据的**唯一实现**（`docs/rules.md` §1）。

判据**不是**「带问号」：真机上她那串自问自答的两句问号都没有，紧接着的定时主动
就把话续上了，用户读到的就是「她替我答了」。所以这一档认六种形状，按优先级
从上往下判，任一命中即为真。

表达层做「剥掉自问自答」时也读这一份 —— 它只有这一个实现，谁要用谁 import，
不许在别处照着写一遍（硬约束 8：评测与实现同源就等于没有评测）。
"""
from __future__ import annotations

import re

__all__ = ["asks_the_user", "ends_with_question"]

# 问号收口：先把尾部那串引号 / 括号削掉再判，否则「真的吗？」后面缀个引号就漏了。
_QUESTION_TAIL = re.compile(r"[？?][”\"'’）)】\]》」』]*\s*$")


def ends_with_question(s: str) -> bool:
    """这一段是不是以问号收口（尾部引号 / 括号不算数）。"""
    return bool(_QUESTION_TAIL.search(str(s or "").strip()))


def asks_the_user(s: str) -> bool:
    """她这一条是不是在**问他**。

    只回答「问过没有」这一件事。用它的地方都把「问过」当成停下来的理由。
    """
    t = str(s or "").strip()
    return ends_with_question(t)