"""宿主注入的四个协议：材料探针、时钟、随机数、切句器。

本库只依赖它们的**形状**，不认识任何实现 —— 也因此在 `import huatou`
之后不会把宿主的记忆层、模型层、传输层带进 `sys.modules`（硬约束 1）。
"""
from __future__ import annotations

from typing import Callable, Iterable, Protocol, runtime_checkable

__all__ = ["Clock", "MaterialProbe", "Rng", "SentenceSplitter"]


@runtime_checkable
class MaterialProbe(Protocol):
    """「手里有没有料」—— 唯一要读库的那一道闸，由记忆层实现。

    它必须是**直查**：闸门跑在「准备这一轮」之前，那时任何缓存的工作面都还是
    上一轮的旧值、而且不一定落盘。判据读缓存的结果是「她永远不开口」，
    看起来像功能坏了（`docs/rules.md` §2.2）。
    """

    def has_material(self) -> bool:
        """事实 / 纪要 / 话题任一有料即为真。"""
        ...


@runtime_checkable
class SentenceSplitter(Protocol):
    """把一段文本切成句子。

    逐字重复那条判据的两边（她说过的话、这一次要出口的第一句）必须过**同一个**
    切句器 —— 注入而不是内置，是为了让「两边同源」这件事在类型上就成立。
    宿主怎么写这一句都行：本库只要求「同一份输入切出同一份结果」。
    """

    def __call__(self, text: str) -> Iterable[str]:
        ...


# 时钟与随机数就是两个无参可调用对象 —— 默认取 `time.time` / `random.random`，
# 但构造 `Floor` 时随时可以换成假的（假时钟是全部时间判据的测试底座）。
Clock = Callable[[], float]
Rng = Callable[[], float]