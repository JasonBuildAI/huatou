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
    """整句相等才算 ——「你好呀，今天楼下特别安静……」是她在真的说话。"""
    assert check("你好呀，今天楼下特别安静……") == ""

def test_only_the_first_sentence_is_judged():
    """后面几条是她展开的内容 —— 拿黑名单去卡会把真的关心话误伤。"""
    assert check("你好。今天楼下特别安静……") == "empty_opener"
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

def test_the_same_sentence_said_again_is_rejected():
    """同一句「今天画了五版」再发一遍，读起来就是她只剩这一句话。"""
    state = State(recent_said=["今天画了五版"])
    assert check("今天画了五版", state=state) == "repeat"


def test_a_half_sentence_hidden_in_an_earlier_message_is_still_a_repeat():
    """真机那个形状：她安静十秒后开口，把上一条消息里的半句一字不差说了一遍。

    历史里一条消息常常挤着好几句，而这一次要出口的是切句之后的一句 ——
    整条对一句永远对不上，所以两边都要过同一个切句器。
    """
    history = "上午在公司，下午改了一版。今天就躺着没起来。"
    state = State(recent_said=[history])
    assert check("今天就躺着没起来", state=state) == "repeat"
    assert check("今天就躺着没起来。", state=state) == "repeat"
    assert check("今天就先躺着", state=state) == ""


def test_repeats_are_compared_after_normalizing_both_sides():
    state = State(recent_said=["今天画了五版。"])
    assert check("今天画了五版！", state=state) == "repeat"
    assert check("今天画了五版～", state=state) == "repeat"


def test_a_different_sentence_is_not_a_repeat():
    state = State(recent_said=["今天画了五版。"])
    assert check("手有点酸", state=state) == ""


def test_only_the_last_dedup_window_messages_are_compared():
    old = "手有点酸"
    state = State(recent_said=[old, "第二句", "第三句"])
    assert check(old, state=state, dials=Dials(dedup_window=2)) == ""
    assert check(old, state=state, dials=Dials(dedup_window=3)) == "repeat"


def test_a_zero_window_turns_the_repeat_check_off():
    state = State(recent_said=["今天画了五版"])
    assert check("今天画了五版", state=state, dials=Dials(dedup_window=0)) == ""

# ---------------------------------------------------------------- 禁用句表
DEFAULT_BANNED = ["你怎么不理我", "你怎么不回答我的问题", "你都不睬我"]


@pytest.mark.parametrize("line", DEFAULT_BANNED)
def test_the_three_promised_lines_are_blocked(line):
    """三层防线里「机器」那一格本来是空的 —— 这三句现在有确定性保障了。"""
    assert check(line) == "banned_line"


@pytest.mark.parametrize("line", ["你怎么不理我。", "你怎么不理我！", " 你怎么不理我 "])
def test_the_banned_list_also_matches_after_normalizing(line):
    assert check(line) == "banned_line"


def test_the_empty_opener_list_is_judged_before_the_banned_list():
    """顺序本身就是判据（rules.md §5）：同一句同时命中两条时，报先判的那一条。

    宿主把「早安」也加进禁用句表（它对这家宿主是硬禁令），理由串仍然是
    `empty_opener` —— 空转名单先跑。
    """
    from huatou.lines import line_rejected

    reason = line_rejected(State(), "早安", dials=Dials(),
                           split_sentences=split_sentences,
                           banned_lines=["早安"])
    assert reason == "empty_opener"


def test_a_host_can_add_its_own_banned_lines():
    from huatou.lines import line_rejected

    extra = ["别问了行吗"]
    assert check("别问了行吗") == "", "宿主不加，就不该被挡"
    assert line_rejected(State(), "别问了行吗", dials=Dials(),
                         split_sentences=split_sentences,
                         banned_lines=extra) == "banned_line"


def test_the_banned_list_does_not_swallow_neighbours():
    """只有整句命中才挡：「你别不理我，我就是顺口一问」是正常在说话。"""
    assert check("你别不理我，我就是顺口一问") == ""


def test_the_banned_list_also_only_judges_the_first_sentence():
    """「你怎么不理我」在第一批里，就是它在指责他 —— 后半句补什么都不能放行。"""
    assert check("你怎么不理我。今天有点累") == "banned_line"
    assert check("你都不睬我。我先去画两笔。") == "banned_line"
