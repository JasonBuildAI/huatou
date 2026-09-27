"""状态：序列化往返与「刷新继承」（`design.md` §3.1、`docs/rules.md` §6）。

刷新继承不是锦上添花：用户刷新页面后，**已经用掉的机会**与「问后等待」都要从
状态里读回来，不因刷新重新布防 —— 否则刷一下就能骗她再问一次。
"""
import json

from huatou.types import State


def _worn_out_state():
    """一份「她已经试过、正在等回话」的状态：每个字段都不是默认值。"""
    return State(streak=2, last_open_ts=1000.5, text_fired=True,
                 waiting_user=True, her_ask_streak=1,
                 recent_said=["今天画了五版", "你呢，今天忙什么呀"],
                 last_activity_ts=999.25)


def test_round_trip_keeps_every_field():
    before = _worn_out_state()
    after = State.from_dict(before.to_dict())
    assert after == before


def test_round_trip_survives_a_real_file_trip():
    """真的过一次 JSON：落盘 / 下发走的就是这条路，别只测内存里的字典。"""
    before = _worn_out_state()
    dumped = json.dumps(before.to_dict(), ensure_ascii=False)
    after = State.from_dict(json.loads(dumped))
    assert after == before


def test_refresh_keeps_the_used_chances_and_the_wait():
    """刷新之后：文字端那一次已经用掉、还在等他回话 —— 两样都得在。"""
    after = State.from_dict(json.loads(json.dumps(_worn_out_state().to_dict())))
    assert after.text_fired is True
    assert after.waiting_user is True
    assert after.streak == 2