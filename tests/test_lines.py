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

def check(line, *, state=None, dials=None):
    from huatou.lines import line_rejected

    return line_rejected(state or State(), line, dials=dials or Dials(),
                         split_sentences=split_sentences)


@pytest.mark.parametrize("line", ["……", "🙂", "。。。", "！？", "   "])
def test_punctuation_and_emoji_are_not_a_line(line):
    assert check(line) == "not_a_line"


def test_a_real_sentence_passes():
    assert check("今天画了五版，手都酸了。") == ""

# 24 条，照 docs/rules.md §5.1 抄写 —— 手抄而不是 import 那份常量，
# 这样「名单被改短了」也能红。
EMPTY_OPENERS = [
    "你好", "您好", "你好呀", "你好啊", "你好哇", "在吗", "你在吗", "在不在",
    "在么", "在嘛", "最近怎么样", "最近好吗", "你最近好吗", "你还好吗",
    "还好吗", "最近还好吗", "早上好", "早安", "哈喽", "hi", "hello",
    "在干嘛", "你在干嘛", "干嘛呢",
]


@pytest.mark.parametrize("line", EMPTY_OPENERS)
def test_every_empty_opener_is_rejected(line):
    assert check(line) == "empty_opener"


@pytest.mark.parametrize("line", ["你好！", " 在吗 ", "Hi", "Hello～", "在干嘛。。"])
def test_the_blacklist_compares_after_normalizing(line):
    """不归一化的话，模型在尾巴上加个标点就绕过去了。"""
    assert check(line) == "empty_opener"


def test_a_greeting_that_keeps_talking_is_not_empty():
    """整句相等才算 ——「你好呀，今天画室特别安静……」是她在真的说话。"""
    assert check("你好呀，今天画室特别安静……") == ""

def test_only_the_first_sentence_is_judged():
    """后面几条是她展开的内容 —— 拿黑名单去卡会把真的关心话误伤。"""
    assert check("你好。今天画室特别安静……") == "empty_opener"
    assert check("今天画了五版，手都酸了。你还好吗？") == ""


def _with_splitter(splitter, line="你好"):
    from huatou.lines import line_rejected

    return line_rejected(State(), line, dials=Dials(), split_sentences=splitter)


def _boom(text):
    raise RuntimeError("切句器坏了")


@pytest.mark.parametrize("splitter", [_boom, lambda text: []])
def test_a_useless_splitter_falls_back_to_the_whole_line(splitter):
    """切句器坏了、或者切不出东西，都不该把话吃掉：退回整条再判。"""
    assert _with_splitter(splitter) == "empty_opener"
    assert _with_splitter(splitter, "今天画了五版") == ""