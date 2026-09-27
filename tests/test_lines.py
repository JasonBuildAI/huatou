"""出稿闸：归一化、黑名单、按句重复、只判第一句（`docs/rules.md` §5）。

切句器一律注入假的那一份 —— 判据的两边必须过同一个切句器，测试里也一样。
"""
import re

import pytest

from huatou.dials import Dials
from huatou.lines import plain_text
from huatou.types import State


def split_sentences(text):
    """最朴素的切句器：句末标点才是边界，逗号不算。"""
    parts = re.split(r"(?<=[。！？!?…])", str(text or ""))
    return [p for p in (part.strip() for part in parts) if p]


@pytest.mark.parametrize("raw,plain", [
    ("你好", "你好"),
    ("你好！", "你好"),
    ("你好。", "你好"),
    ("你好～", "你好"),
    ("  Hi  ", "hi"),
    ("Hello!", "hello"),
    ("……", ""),
    ("🙂🙂", ""),
    ("今天画了五版，手都酸了。", "今天画了五版手都酸了"),
])
def test_plain_text_keeps_only_the_words(raw, plain):
    assert plain_text(raw) == plain


def test_plain_text_never_raises_on_odd_input():
    assert plain_text(None) == ""
    assert plain_text(3.14) == "314"