"""「她有没有在问他」：六种形状各一组正反例（`docs/rules.md` §1）。

真机句子一律照抄，不做改写 —— 它们是这条判据的证据，改写过的例子证明不了任何事。
"""
import pytest

from huatou.ask import asks_the_user, ends_with_question


@pytest.mark.parametrize("text", [
    "今天忙什么？",
    "你到宿舍了吗?",
    "刚刚那事，你还记得？",
    "说过「真的吗？」",          # 问号后面还有引号，也要认
    "这样也行？？",
])
def test_shape_1_question_mark_tail(text):
    assert asks_the_user(text)


@pytest.mark.parametrize("text", [
    "",
    "嗯。",
    "今天画了五版",
    "好，我知道了。",
    "刚刚那事你还记得",
])
def test_shape_1_rejects_everything_else(text):
    assert not asks_the_user(text)


def test_ends_with_question_only_looks_at_the_tail():
    assert ends_with_question("是吗？")
    assert not ends_with_question("？真的吗")

@pytest.mark.parametrize("text", [
    "最近怎么了呀",                              # 真机 2026-09-23 通话
    "你们宿舍现在还剩几个能一块吃饭的",           # 真机 2026-09-23 判定式评测
    "你们宿舍一般谁先开口挑明",                   # 同上
    "验收前还要改几天呀",                         # 真机 2026-09-23 晚
    "这个项目还要熬几天",                         # 同上
    "是那种闷闷的，还是有点空落落的",              # 选择问句，真机
    "今天几点睡的",
    "这样好不好嘛",
    "你知不知道我在哪儿",
])
def test_shape_2_question_words(text):
    assert asks_the_user(text)


@pytest.mark.parametrize("text", [
    "没什么事，就是有点困",
    "不怎么想说话",
    "哪有那种事",
])
def test_shape_2_negative_prefixes_are_statements(text):
    """否定前缀那几格要真的挡得住 —— 它们读起来是陈述，不是问句。"""
    assert not asks_the_user(text)