"""口径与状态这两个公开类型的契约。"""
from huatou.types import Channel


def test_channel_is_a_string_enum():
    """宿主会把它写进 JSON、当字典键 —— 所以它必须是 str 的子类。"""
    assert Channel.TEXT == "text"
    assert Channel.CALL == "call"
    assert isinstance(Channel.CALL, str)


def test_channel_coerce_accepts_strings_and_itself():
    assert Channel.coerce("call") is Channel.CALL
    assert Channel.coerce(" TEXT ") is Channel.TEXT
    assert Channel.coerce(Channel.CALL) is Channel.CALL


def test_channel_coerce_falls_back_to_text():
    """认不出来的档按**更保守**的文字档走，不抛异常、不静默成通话档。"""
    assert Channel.coerce("voice") is Channel.TEXT
    assert Channel.coerce(None) is Channel.TEXT
    assert Channel.coerce(3) is Channel.TEXT

def test_verdict_carries_a_reason_in_both_directions():
    """放行也要有理由串 —— 面板上那两列是同一套写法，不许一边空着。"""
    from huatou.types import Verdict

    yes = Verdict.allow()
    no = Verdict.deny("no_material", "手里一点素材都没有")
    assert yes.allowed and yes.reason == "ok"
    assert not no.allowed and no.reason == "no_material"
    assert no.detail == "手里一点素材都没有"


def test_verdict_is_frozen():
    """判定结果是值对象：拿到手之后谁都不许改它。"""
    import dataclasses

    import pytest

    from huatou.types import Verdict

    v = Verdict.deny("waiting_user")
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.allowed = True

def test_state_starts_as_a_session_that_never_opened_itself():
    """默认值 = 一个刚从没主动开过口的新会话；老宿主不做迁移也能跑。"""
    from huatou.types import State

    s = State()
    assert (s.streak, s.last_open_ts, s.her_ask_streak) == (0, 0.0, 0)
    assert s.text_fired is False
    assert s.waiting_user is False
    assert s.recent_said == []
    assert s.last_activity_ts == 0.0


def test_each_state_gets_its_own_recent_said_list():
    """`recent_said` 不能是类属性那种共享的可变默认值。"""
    from huatou.types import State

    a, b = State(), State()
    a.recent_said.append("你好")
    assert b.recent_said == []

def test_to_dict_is_json_ready_and_does_not_lend_out_the_list():
    """落盘的形状要能直接 json.dumps；`recent_said` 必须是副本。"""
    import json

    from huatou.types import State

    s = State(streak=1, last_open_ts=100.5, text_fired=True,
              waiting_user=True, her_ask_streak=2,
              recent_said=["你好", "在干嘛"], last_activity_ts=99.0)
    d = s.to_dict()
    assert json.loads(json.dumps(d)) == d

    d["recent_said"].append("别的话")
    assert s.recent_said == ["你好", "在干嘛"]


def test_to_dict_repairs_sloppy_values():
    """状态可能来自旧版本或被人手改过：出口这一道要能收得住坏值。"""
    from huatou.types import State

    s = State(streak=None, last_open_ts=None, her_ask_streak=None,
              recent_said=None, last_activity_ts=None)
    assert s.to_dict() == {
        "streak": 0, "last_open_ts": 0.0, "text_fired": False,
        "waiting_user": False, "her_ask_streak": 0, "recent_said": [],
        "last_activity_ts": 0.0,
    }

def test_from_dict_never_raises_on_sloppy_input():
    """失败姿态是放宽：认不出形状就取默认，绝不把异常抛给宿主。"""
    from huatou.types import State

    assert State.from_dict(None) == State()
    assert State.from_dict("不是字典") == State()
    assert State.from_dict({"streak": "坏了", "last_open_ts": float("nan"),
                            "recent_said": 42, "her_ask_streak": []}) == State()


def test_from_dict_reads_strings_and_numbers_as_written():
    from huatou.types import State

    s = State.from_dict({"streak": "3", "text_fired": "false",
                         "waiting_user": "true", "recent_said": "一句话",
                         "last_activity_ts": "12.5"})
    assert s.streak == 3
    assert s.text_fired is False
    assert s.waiting_user is True
    assert s.recent_said == ["一句话"]
    assert s.last_activity_ts == 12.5


def test_from_dict_ignores_keys_it_does_not_know():
    """多余的键忽略掉 —— 别的模块往同一份状态里塞过东西也不会读崩。"""
    from huatou.types import State

    s = State.from_dict({"streak": 1, "reply_mode": "voice", "未来字段": [1, 2]})
    assert s == State(streak=1)

def test_from_dict_treats_the_old_boolean_as_one_round_of_asking():
    """老状态只有一个布尔量：读成「连问了 1 轮」，她还能再问一轮，不会永远卡住。"""
    from huatou.types import State

    assert State.from_dict({"last_her_ask": True}).her_ask_streak == 1
    assert State.from_dict({"last_her_ask": False}).her_ask_streak == 0


def test_new_field_wins_over_the_old_boolean():
    """两个都在场时以新的为准 —— 布尔量只是迁移期的替身。"""
    from huatou.types import State

    assert State.from_dict({"her_ask_streak": 2, "last_her_ask": True}).her_ask_streak == 2