"""阈值表：默认值、分档取值、以及「改了就变」。

默认值这一条是**照着 `docs/rules.md` §3.2 抄下来的**：那张表是唯一真源，
这里逐项钉住，改数字必须两边一起改（只改一边时这条会红）。
"""
import pytest

from huatou.dials import Dials
from huatou.types import Channel

DOCUMENTED_DEFAULTS = {
    "open_text_sec": 10,
    "open_call_sec": 4,
    "max_streak": 2,
    "min_gap_sec": 8,
    "hand_back_ratio_text": 1.0,
    "hand_back_ratio_call": 0.95,
    "hand_back_min_units_text": 4,
    "hand_back_min_units_call": 2,
    "max_ask_streak": 2,
    "dedup_window": 5,
}


@pytest.mark.parametrize("field,expected", sorted(DOCUMENTED_DEFAULTS.items()))
def test_defaults_match_the_documented_table(field, expected):
    assert getattr(Dials(), field) == expected


def test_defaults_are_a_fresh_copy_each_time():
    """改一份不许串到下一份 —— 阈值是每个宿主自己的东西。"""
    a = Dials()
    a.open_text_sec = 99.0
    assert Dials().open_text_sec == 10.0


@pytest.mark.parametrize("channel,open_sec,ratio,units", [
    (Channel.TEXT, 10.0, 1.0, 4),
    (Channel.CALL, 4.0, 0.95, 2),
    ("call", 4.0, 0.95, 2),
    ("text", 10.0, 1.0, 4),
])
def test_per_channel_readers(channel, open_sec, ratio, units):
    d = Dials()
    assert d.open_sec(channel) == open_sec
    assert d.hand_back_ratio(channel) == ratio
    assert d.hand_back_min_units(channel) == units


def test_unknown_channel_reads_the_text_column():
    """认不出来的档按更保守的文字档 —— 与 Channel.coerce 同一取向。"""
    d = Dials()
    assert d.open_sec("voice") == d.open_text_sec
    assert d.hand_back_min_units(None) == d.hand_back_min_units_text


def test_with_changes_leaves_the_original_alone():
    d = Dials()
    other = d.with_changes(max_streak=0)
    assert other.max_streak == 0 and d.max_streak == 2