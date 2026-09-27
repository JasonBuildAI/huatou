"""主动开口的放行闸与布防时长（`docs/rules.md` §2、§3）。

全部时间判据都走假时钟与假探针：测试里不许出现真 `sleep`、真 `time.time()`。
"""
from huatou.dials import Dials
from huatou.opening import may_open
from huatou.types import Channel, State


class Probe:
    """假材料探针：记下被调用了几次，也可以装死。"""

    def __init__(self, material=True, error=None):
        self.material = material
        self.error = error
        self.calls = 0

    def has_material(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.material


def check(state=None, *, channel=Channel.TEXT, now=1000.0, dials=None, probe=None):
    return may_open(state or State(), channel=channel, now=now,
                    dials=dials or Dials(), material=probe or Probe())


def test_zero_max_streak_is_a_switch_not_a_threshold():
    """0 = 关掉这个功能 —— 它是开关，所以第一道就判它。"""
    probe = Probe()
    v = check(dials=Dials(max_streak=0), probe=probe)
    assert not v.allowed
    assert v.reason == "disabled"
    assert probe.calls == 0, "关掉的功能不该再往下判，更不该开库"


def test_a_quiet_new_state_is_allowed():
    """刚开的新会话、什么都不挡时放行 —— 理由串照样是「ok」。"""
    v = check()
    assert v.allowed and v.reason == "ok"

def test_waiting_for_him_blocks_the_next_open():
    """她问过之后：没等到他真实开口就不再开口 —— 再定时追问像催促。"""
    probe = Probe()
    v = check(State(waiting_user=True), probe=probe)
    assert not v.allowed and v.reason == "waiting_user"
    assert probe.calls == 0

def test_text_side_only_gets_one_proactive_try_per_turn():
    """文字端一个真实回合只主动挑一次；通话档不受这一条限制。"""
    fired = State(text_fired=True)
    assert check(fired, channel=Channel.TEXT).reason == "text_fired"
    assert check(fired, channel=Channel.CALL).allowed

def test_the_streak_limit_is_terminal_until_he_speaks():
    """「她试了两次就不再打扰你」：到了上限就不再布防，直到他开口。"""
    assert check(State(streak=1)).allowed
    denied = check(State(streak=2))
    assert not denied.allowed and denied.reason == "max_streak"
    assert check(State(streak=9)).reason == "max_streak"


def test_a_bigger_limit_lets_her_try_more():
    """上限现读：同一条状态，宿主把 max_streak 调大就放行（硬约束 5）。"""
    assert check(State(streak=3), dials=Dials(max_streak=4)).allowed

def test_not_quiet_enough_blocks_when_the_host_recorded_activity():
    """假时钟钉死这一档：9.9 秒不放行、10.1 秒放行。"""
    dials = Dials(open_text_sec=10)
    state = State(last_activity_ts=1000.0)

    denied = check(state, now=1009.9, dials=dials)
    assert not denied.allowed and denied.reason == "quiet"
    assert check(state, now=1010.1, dials=dials).allowed


def test_without_an_activity_record_the_quiet_gate_stays_out_of_the_way():
    """没有活动时间戳时，沉默归布防侧管 —— 服务端不假装知道。"""
    assert check(State()).allowed


def test_the_quiet_threshold_follows_the_channel():
    dials = Dials(open_call_sec=4)
    state = State(last_activity_ts=1000.0)
    assert check(state, channel=Channel.CALL, now=1003.9, dials=dials).reason == "quiet"
    assert check(state, channel=Channel.CALL, now=1004.1, dials=dials).allowed

def test_two_opens_must_be_far_enough_apart():
    """两次主动之间至少隔 8 秒 —— 7.9 秒挡、8.1 秒放。"""
    dials = Dials(min_gap_sec=8)
    state = State(last_open_ts=1000.0)
    assert check(state, now=1007.9, dials=dials).reason == "min_gap"
    assert check(state, now=1008.1, dials=dials).allowed


def test_the_gap_is_measured_from_the_last_open_not_from_now():
    """锚点是「上一次主动开口」，不是「刚刚」—— 状态里那个时间戳说了算。"""
    dials = Dials(min_gap_sec=8)
    assert check(State(last_open_ts=0.0), now=1000.0, dials=dials).allowed

def test_two_opens_must_be_far_enough_apart():
    """两次主动之间至少隔 8 秒 —— 7.9 秒挡、8.1 秒放。"""
    dials = Dials(min_gap_sec=8)
    state = State(last_open_ts=1000.0)
    assert check(state, now=1007.9, dials=dials).reason == "min_gap"
    assert check(state, now=1008.1, dials=dials).allowed


def test_the_gap_is_measured_from_the_last_open_not_from_now():
    """锚点是「上一次主动开口」那个时间戳，不是「刚刚」。"""
    dials = Dials(min_gap_sec=8)
    assert check(State(last_open_ts=0.0), now=1000.0, dials=dials).allowed

def test_no_material_means_no_opening():
    """没料就不开口 —— 这一条是产品判据，不是省钱判据。"""
    empty = Probe(material=False)
    denied = check(probe=empty)
    assert not denied.allowed and denied.reason == "no_material"

    full = Probe(material=True)
    assert check(probe=full).allowed
    assert (empty.calls, full.calls) == (1, 1), "放行与不放行各查一次库，不多查"

def test_a_broken_probe_degrades_to_silence_but_says_why():
    """探针坏了：这次不开口，但理由串要把「为什么」答出来，不许静默。"""
    boom = Probe(error=RuntimeError("库打不开"))
    denied = check(probe=boom)
    assert not denied.allowed and denied.reason == "material_error"
    assert "库打不开" in denied.detail
    assert boom.calls == 1