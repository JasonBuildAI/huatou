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