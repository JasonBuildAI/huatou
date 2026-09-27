"""四个注入协议的契约：形状对了就行，不要求继承。"""
from huatou.protocols import MaterialProbe, SentenceSplitter


def test_any_object_with_has_material_counts_as_a_probe():
    class Fake:
        def has_material(self):
            return True

    assert isinstance(Fake(), MaterialProbe)
    assert not isinstance(object(), MaterialProbe)


def test_any_callable_that_takes_text_counts_as_a_splitter():
    def split(text):
        return [text]

    assert isinstance(split, SentenceSplitter)
    assert not isinstance("不是可调用对象", SentenceSplitter)