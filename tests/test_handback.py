"""递话头：长度闸、连问闸、抽签（`docs/rules.md` §4）。

rng 一律注入假序列 —— 抽中与没抽中两个方向都要被钉死。
"""
import pytest

from huatou.dials import Dials
from huatou.handback import length_units, should_hand_back
from huatou.types import Channel, State


def roll(value):
    """假 rng：永远返回同一个数。"""
    return lambda: value


def check(state=None, *, channel=Channel.TEXT, user_msg="今天加班到几点才回来",
          dials=None, rng=0.0):
    return should_hand_back(state or State(), channel=channel, user_msg=user_msg,
                            dials=dials or Dials(), rng=roll(rng))


@pytest.mark.parametrize("msg,units", [
    ("", 0),
    ("嗯", 1),
    ("还行", 2),
    ("就 那 样", 3),
    ("我喜欢", 3),
    ("今天加班到几点才回来", 10),
])
def test_length_is_counted_without_whitespace(msg, units):
    assert length_units(msg) == units


def test_text_side_needs_four_units():
    """文字端 4 字以下不抽 —— 那几个字没什么可接的。"""
    assert check(user_msg="嗯").reason == "too_short"
    assert check(user_msg="还行吧你").allowed


def test_call_side_settles_for_two():
    """通话档只要求 2 字：那边大半句是「嗯。」「我喜欢。」，4 字闸会挡掉大半轮。"""
    short = "我喜欢"
    assert check(channel=Channel.CALL, user_msg=short).allowed
    assert check(channel=Channel.TEXT, user_msg=short).reason == "too_short"