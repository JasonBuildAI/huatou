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