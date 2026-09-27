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
    """`rng` 给一个数就当成「每次都返回它」，给一个可调用对象就直接用它。"""
    return should_hand_back(state or State(), channel=channel, user_msg=user_msg,
                            dials=dials or Dials(),
                            rng=rng if callable(rng) else roll(rng))


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

def test_two_rounds_of_asking_in_a_row_stop_the_third():
    """连问闸的粒度是「一段」：问过还能再问一轮，第三轮必停。"""
    assert check(State(her_ask_streak=1)).allowed
    denied = check(State(her_ask_streak=2))
    assert not denied.allowed and denied.reason == "ask_streak"
    assert check(State(her_ask_streak=5)).reason == "ask_streak"


def test_the_ask_streak_limit_is_read_at_call_time():
    """上限现读：同一条状态，宿主把它抬到 3 就放行（硬约束 5）。"""
    assert check(State(her_ask_streak=2), dials=Dials(max_ask_streak=3)).allowed

# ---------------------------------------------------------------- 抽签
class CountingRng:
    """假 rng：返回固定值，同时记下被调用了几次。"""

    def __init__(self, value=0.0, error=None):
        self.value = value
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.value


def test_half_the_time_it_is_allowed_and_half_the_time_it_is_not():
    """两个方向都被假 rng 钉死 —— 概率式指令服从度不稳，抽签必须可复现。"""
    dials = Dials(hand_back_ratio_text=0.5)
    assert check(dials=dials, rng=0.49).allowed
    assert check(dials=dials, rng=0.5).reason == "roll"
    assert check(dials=dials, rng=0.99).reason == "roll"


def test_the_call_channel_ratio_is_higher():
    """通话档 0.95：他每句都短、常被 VAD 切碎，机会本来就少。"""
    dials = Dials()
    assert check(channel=Channel.CALL, dials=dials, rng=0.94).allowed
    assert check(channel=Channel.CALL, dials=dials, rng=0.96).reason == "roll"


def test_a_broken_rng_degrades_to_not_handing_back_but_says_why():
    denied = check(rng=CountingRng(error=RuntimeError("没有随机源")))
    assert not denied.allowed and denied.reason == "rng_error"
    assert "没有随机源" in denied.detail

def test_the_draw_is_not_consumed_when_an_earlier_gate_blocks():
    """抽签放最后：被挡住时一个随机数都不许消费，不然两个信号会混在一起。"""
    rng = CountingRng(0.0)
    assert should_hand_back(State(), channel=Channel.TEXT, user_msg="嗯",
                            dials=Dials(), rng=rng).reason == "too_short"
    assert should_hand_back(State(her_ask_streak=2), channel=Channel.TEXT,
                            user_msg="今天加班到几点才回来",
                            dials=Dials(), rng=rng).reason == "ask_streak"
    assert rng.calls == 0


def test_the_draw_is_consumed_exactly_once_when_both_gates_pass():
    rng = CountingRng(0.0)
    assert should_hand_back(State(), channel=Channel.TEXT,
                            user_msg="今天加班到几点才回来",
                            dials=Dials(), rng=rng).allowed
    assert rng.calls == 1