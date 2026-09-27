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