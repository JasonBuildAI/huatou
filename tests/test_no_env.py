"""硬约束 12：库内部不许读环境变量（`docs/rules.md` §7）。

配置由宿主显式传进 `Dials`，或由宿主自己从环境变量组装。一个库背着调用方去读
环境，症状是「我以为它没配，它却在按别的规则走」—— 而 huatou 的整条立库理由
就是把这种「说不清它为什么这么判」的隐式来源清掉。

这份护栏扫的是源码文本，不是运行时行为：它要能在**新增一行读取**时立刻红，
而不是等某台机器上的环境变量恰好不对才红。
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = sorted((ROOT / "huatou").glob("*.py"))

# 读取环境变量的写法：`os.environ[...]` / `os.environ.get(...)` / `os.getenv(...)` /
# `getenv(...)`（`from os import getenv` 的形状）。注释与文档里提到它不算违规 ——
# 但本库连提都不提，所以不做豁免，命中即红。
_ENV_READ = re.compile(r"(?:os\.)?(?:environ\s*(?:\.get)?|getenv)\s*[\[(.]")


def env_reads(text: str) -> list:
    """这份源码里读环境变量的行号（从 1 数）。"""
    hits = []
    for number, line in enumerate(str(text).splitlines(), start=1):
        if _ENV_READ.search(line):
            hits.append(number)
    return hits


def test_the_pattern_actually_catches_an_env_read():
    """先证明这条判据能红：拿一行真的读取喂给它，必须认出第 2 行。"""
    sample = "x = 1\ny = os.getenv('HUATOU_X')\nz = os.environ['Y']\n"
    assert env_reads(sample) == [2, 3]


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_the_package_never_reads_the_environment(path):
    assert env_reads(path.read_text(encoding="utf-8")) == []


def test_the_scan_covers_every_source_file():
    """扫的文件就是包里的全部 —— 新增模块自动进场，不用改这份名单。"""
    names = [p.name for p in SOURCES]
    assert "floor.py" in names and "opening.py" in names
    assert names == sorted(names)
