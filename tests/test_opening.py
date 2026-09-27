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