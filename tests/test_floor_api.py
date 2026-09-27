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

# ---------------------------------------------------------------- 状态推进
def test_the_user_speaking_clears_everything_and_rearms():
    """用户真实说话是唯一能把这些一起清掉的信号。"""
    floor, clock, _ = make_floor(now=2000.0)
    state = State(streak=2, last_open_ts=1500.0, text_fired=True,
                  waiting_user=True, her_ask_streak=2, recent_said=["说过的话"])
    floor.note_user_spoke(state)

    assert state.streak == 0
    assert state.last_open_ts == 0.0
    assert state.text_fired is False
    assert state.waiting_user is False
    assert state.her_ask_streak == 0
    assert state.last_activity_ts == 2000.0, "沉默从「他刚说完」重新算起"
    assert state.recent_said == ["说过的话"], "他说过话不代表她没说过那几句"


def test_note_star_timestamps_can_be_given_explicitly():
    """时间戳也能由宿主递进来 —— 假时钟之外的第二条确定性路子。"""
    floor, _, _ = make_floor(now=2000.0)
    state = State()
    floor.note_user_spoke(state, now=1234.5)
    assert state.last_activity_ts == 1234.5

def test_opening_herself_counts_up_and_stamps_the_time():
    floor, _, _ = make_floor()
    state = State()
    floor.note_opened(state, channel=Channel.TEXT, now=1500.0)
    assert state.streak == 1
    assert state.last_open_ts == 1500.0
    assert state.last_activity_ts == 1500.0
    assert state.text_fired is True


def test_only_the_text_channel_marks_the_text_chance_as_used():
    """通话档不写 `text_fired`：它压的是「文字端这一回合已经挑过一次」。"""
    floor, _, _ = make_floor()
    state = State()
    floor.note_opened(state, channel=Channel.CALL, now=1500.0)
    assert state.text_fired is False
    assert state.streak == 1, "通话档照样算连续主动的一次"


def test_two_opens_in_a_row_hit_the_limit():
    """连开两次之后，第三次就不放行了 —— 时钟与两个计时器都放过它之后才轮到上限。"""
    floor, _, _ = make_floor(now=30.0)
    state = State()
    floor.note_opened(state, channel=Channel.CALL, now=1.0)
    floor.note_opened(state, channel=Channel.CALL, now=20.0)
    assert state.streak == 2
    assert floor.may_open(state, channel=Channel.CALL).reason == "max_streak"

def test_what_she_said_is_kept_so_the_repeat_check_has_something_to_compare():
    floor, _, _ = make_floor()
    state = State()
    floor.note_said(state, "今天画了五版")
    assert state.recent_said == ["今天画了五版"]
    assert floor.line_rejected(state, "今天画了五版") == "repeat"


def test_the_window_keeps_the_state_from_growing_with_every_turn():
    floor, _, _ = make_floor()
    state = State()
    for i in range(9):
        floor.note_said(state, f"第 {i} 条")
    assert len(state.recent_said) == 5, "窗口默认 5 条，多出来的丢掉"
    assert state.recent_said[-1] == "第 8 条"
    assert floor.line_rejected(state, "第 3 条") == "", "早就不在窗口里的不算重复"


def test_an_empty_message_is_not_recorded():
    floor, _, _ = make_floor()
    state = State()
    floor.note_said(state, "")
    floor.note_said(state, "   ")
    assert state.recent_said == []


def test_the_trim_window_is_read_at_call_time():
    """窗口现读：宿主把 dedup_window 调小，下一次记就把多的裁掉。"""
    floor, _, _ = make_floor()
    state = State()
    floor.note_said(state, "第一句")
    floor.note_said(state, "第二句")
    floor.dials = Dials(dedup_window=1)
    floor.note_said(state, "第三句")
    assert state.recent_said == ["第三句"]