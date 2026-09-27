"""隐私护栏：源产品的角色名、产品名与身份词不许外带（`design.md` §9 第 1 条）。

名单以**码点**存。这份护栏文件自己就躺在公开仓库里 —— 它要是把名字写成明文，
要挡的那个名字照样泄漏了，还多一处要被搜到的位置。每条都带一句理由：
没有理由的名单，下一个人会当成误报删掉。

扫描范围是**我们自己往外写的东西**（代码、测试、示范、README、rules、integration）；
`docs/design.md` 不在范围里 —— 它是外部输入（仓库主人写的施工说明），
里面点名了源仓库和源材料，删不掉也不该由这份护栏管。
"""
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _word(*codes):
    """把码点拼回字符串 —— 名单里只出现数字。"""
    return "".join(chr(int(code)) for code in codes)


# 名单：一条一条写清「为什么它不许出现」。
FORBIDDEN = (
    (_word(0x6797, 0x4E00, 0x6B23),
     "源产品的人设角色名：本库是公开库，角色身份不外带（design.md §9 第 1 条）"),
    (_word(0x6E, 0x75, 0x6D, 0x62, 0x65, 0x72, 0x68, 0x75, 0x6D, 0x61, 0x6E),
     "源产品的仓库名：接缝在这里，源产品不该被写进公开库"),
    (_word(0x9EC4, 0x6C5F, 0x5357),
     "源仓库作者的用户名：会随本机路径一起泄漏，与本库的判据毫无关系"),
    (_word(0x753B, 0x5ECA),
     "源角色的人设身份词（她的职业场地）：判据不需要它，带进来只是泄漏设定"),
    (_word(0x753B, 0x5BA4),
     "源角色的人设身份词（她待的地方）：同上，是设定不是判据"),
)

SCANNED = [
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / "docs" / "rules.md",
    ROOT / "docs" / "integration.md",
    *sorted((ROOT / "huatou").glob("*.py")),
    *sorted((ROOT / "tests").glob("*.py")),
    *sorted((ROOT / "examples").glob("*.py")),
]


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def test_every_entry_has_a_reason_and_decodes():
    """名单本身的两条自检：码点拼得回字符串，每条都有一句理由。"""
    assert len(FORBIDDEN) >= 5
    for word, why in FORBIDDEN:
        assert word and isinstance(word, str)
        assert len(why) >= 10, "理由要写够一句话，不然删名字的人不知道该不该删"


def test_the_guard_file_itself_does_not_leak_any_name():
    """护栏文件自己也不能带明文 —— 这正是名单存码点的理由。"""
    text = read(pathlib.Path(__file__))
    for word, _why in FORBIDDEN:
        assert word not in text


def test_the_scan_covers_the_files_we_publish():
    """扫到的名单要覆盖 README、三份 docs 与示范；design.md 明确不在里面。"""
    names = {path.name for path in SCANNED}
    assert {"README.md", "rules.md", "integration.md", "ci.yml", "companion.py"} <= names
    package = {path.name for path in SCANNED if path.parent.name == "huatou"}
    assert {"opening.py", "lines.py", "floor.py", "ask.py"} <= package
    assert (ROOT / "docs" / "design.md") not in SCANNED


@pytest.mark.parametrize("path", SCANNED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_forbidden_name_appears(path):
    text = read(path)
    for word, why in FORBIDDEN:
        assert word not in text, f"{path.name} 里出现了不该外带的名字（{why}）"
