"""门面契约：判定不改状态，注入的东西调用时现读（`docs/rules.md` §6、§7）。

这一份文件里的时钟与随机数全是假的 —— 判定不该自己去问真时间。
"""
import re

import pytest

from huatou.dials import Dials
from huatou.floor import Floor
from huatou.types import Channel, State


class Probe:
    def __init__(self, material=True, error=None):
        self.material = material
        self.error = error
        self.calls = 0

    def has_material(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.material


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


def split_sentences(text):
    parts = re.split(r"(?<=[。！？!?…])", str(text or ""))
    return [p for p in (part.strip() for part in parts) if p]


def make_floor(*, now=1000.0, material=True, rng=0.0, dials=None, banned_lines=()):
    clock = FakeClock(now)
    probe = Probe(material=material)
    return Floor(dials=dials or Dials(), material=probe, split_sentences=split_sentences,
                 clock=clock, rng=lambda: rng, banned_lines=banned_lines), clock, probe


def test_the_facade_answers_the_same_as_the_module_functions():
    floor, _, _ = make_floor()
    state = State(last_activity_ts=900.0, last_open_ts=900.0)
    assert floor.may_open(state, channel=Channel.TEXT).allowed
    assert floor.arm_after(state, channel=Channel.TEXT) == 0.0
    assert floor.should_hand_back(state, channel=Channel.TEXT,
                                  user_msg="今天加班到几点才回来").allowed
    assert floor.must_wait(State(waiting_user=True)) is True
    assert floor.line_rejected(State(), "你好") == "empty_opener"
    assert floor.asks_the_user("最近怎么了呀") is True


def test_every_injection_is_read_at_call_time():
    """注入的东西是**调用时**现读：换掉它们，下一次判定就跟着变。"""
    floor, clock, probe = make_floor(now=1000.0)
    state = State(last_activity_ts=900.0, last_open_ts=900.0)
    assert floor.may_open(state, channel=Channel.TEXT).allowed

    floor.dials = Dials(min_gap_sec=99999)
    assert floor.may_open(state, channel=Channel.TEXT).reason == "min_gap"

    floor.dials = Dials(hand_back_ratio_text=0.5)
    assert floor.should_hand_back(state, channel=Channel.TEXT,
                                  user_msg="今天加班到几点才回来").allowed
    floor.rng = lambda: 1.0
    assert floor.should_hand_back(state, channel=Channel.TEXT,
                                  user_msg="今天加班到几点才回来").reason == "roll"

    probe.material = False
    assert floor.may_open(state, channel=Channel.TEXT).reason == "no_material"

    # 时钟也是现读：安静够了（1005 - 900），但距上一次主动开口只过了 5 秒
    clock.now = 1005.0
    state.last_open_ts = 1000.0
    assert floor.may_open(state, channel=Channel.TEXT).reason == "min_gap"


def test_the_floor_keeps_no_time_of_its_own():
    """时钟只有一个来源：注入的那个。判定不去问真时间。"""
    floor, clock, _ = make_floor(now=1000.0)
    state = State(last_activity_ts=1000.0)
    assert floor.arm_after(state, channel=Channel.TEXT) == pytest.approx(10.0)
    clock.now = 1005.0
    assert floor.arm_after(state, channel=Channel.TEXT) == pytest.approx(5.0)