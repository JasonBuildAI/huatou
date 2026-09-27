"""一个假宿主的完整示范：假时钟 + 假材料 + 假切句器。

跑法（两选一，都在仓库根）：

```powershell
python -m huatou demo
python examples/companion.py
```

它演一遍完整的状态机：他打开页面 → 安静够久 → 她主动开口 → 她问了问题 →
**她等他回话**（这期间定时器再来也不放行）→ 他开口 → 重新布防 → 连开两次 →
到了终局 → 再等他说话。中间顺手演一遍出稿闸与「刷新继承」。

这份示范不 import 任何宿主实现：材料探针、时钟、切句器都是这里现写的假的。
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

# 直接 `python examples/companion.py` 跑时，sys.path[0] 是 examples/ 而不是仓库根；
# 把仓库根补进去，两种跑法（这个文件、`python -m huatou demo`）才都成立。
_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from huatou import Channel, Dials, Floor, State  # noqa: E402

# 她记得的东西（真宿主里这是记忆层直查的结果，本库不认识它长什么样）。
MATERIAL = ["他上周提过要去做体检"]


class FakeClock:
    """假时钟：时间由剧本推进，不由真实世界推进。"""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> float:
        self.now += seconds
        return self.now


class FakeMaterial:
    """假材料探针：直查「手里有没有料」，不读任何缓存。"""

    def __init__(self, items=None) -> None:
        self.items = list(MATERIAL if items is None else items)

    def has_material(self) -> bool:
        return bool(self.items)


def split_sentences(text):
    """最朴素的切句器：句末标点才是边界，逗号不算。"""
    parts = re.split(r"(?<=[。！？!?…])", str(text or ""))
    return [part for part in (p.strip() for p in parts) if part]


def _show(clock, what: str) -> None:
    print(f"[{clock.now:6.1f}s] {what}")


def main(argv=None) -> int:
    clock = FakeClock()
    floor = Floor(dials=Dials(), material=FakeMaterial(),
                  split_sentences=split_sentences, clock=clock, rng=lambda: 0.4)
    state = State()

    _show(clock, "他打开页面。布防：")
    wait = floor.arm_after(state, channel=Channel.TEXT)
    _show(clock, f"  还要安静 {wait:.0f} 秒才该请求一次（文字档）")
    assert wait == 10.0

    clock.advance(wait)
    verdict = floor.may_open(state, channel=Channel.TEXT)
    _show(clock, f"安静够了，问一次：{verdict.allowed} / {verdict.reason}")
    assert verdict.allowed

    opening_line = "今天画了五版，手都酸了。你呢，最近还在熬夜吗"
    rejected = floor.line_rejected(state, opening_line)
    asks = floor.asks_the_user(opening_line)
    _show(clock, f"她这句能不能出口：{rejected or '可以'}；她在问他吗：{asks}")
    assert not rejected and asks

    floor.note_opened(state, channel=Channel.TEXT)
    floor.note_said(state, opening_line)
    floor.note_her_ask(state, asks)
    _show(clock, f"她开口了：连续 {state.streak} 次，正在等他回话：{state.waiting_user}")
    assert state.streak == 1 and state.text_fired and state.waiting_user

    clock.advance(3)
    late = floor.may_open(state, channel=Channel.TEXT)
    _show(clock, f"才过 3 秒，再问一次：{late.allowed} / {late.reason}（她问过，等他回话）")
    assert not late.allowed and late.reason == "waiting_user"

    clock.advance(20)
    still_waiting = floor.may_open(state, channel=Channel.TEXT)
    _show(clock, f"他没回话，安静 23 秒了：{still_waiting.allowed} / {still_waiting.reason}")
    assert not still_waiting.allowed and still_waiting.reason == "waiting_user"

    _show(clock, "他终于说话了。")
    hand = floor.should_hand_back(state, channel=Channel.TEXT,
                                  user_msg="今天还是没睡好，三点才睡着")
    _show(clock, f"答完要不要把话头递回去：{hand.allowed} / {hand.reason}")
    assert hand.allowed
    too_short = floor.should_hand_back(state, channel=Channel.TEXT, user_msg="嗯")
    _show(clock, f"他只有一句「嗯」：{too_short.allowed} / {too_short.reason}（长度闸）")
    assert not too_short.allowed and too_short.reason == "too_short"

    floor.note_user_spoke(state)
    _show(clock, f"他一开口，全部清零：连续 {state.streak} 次，"
                 f"等他回话：{state.waiting_user}")

    clock.advance(10)
    second = floor.may_open(state, channel=Channel.TEXT)
    _show(clock, f"第二个真实回合：{second.allowed} / {second.reason}")
    floor.note_opened(state, channel=Channel.TEXT)
    floor.note_said(state, "那今晚早点睡，别又熬到三点。")
    floor.note_her_ask(state, False)          # 这一句没在问他
    retry = floor.may_open(state, channel=Channel.TEXT)
    _show(clock, f"文字端这一回合再挑一次：{retry.allowed} / {retry.reason}")
    _show(clock, f"  这时候的布防：{floor.arm_after(state, channel=Channel.TEXT)}")
    assert not retry.allowed and retry.reason == "text_fired"
    assert floor.arm_after(state, channel=Channel.TEXT) is None

    _show(clock, "他改打电话（通话档，另一个口气档）：")
    floor.note_user_spoke(state)
    clock.advance(5)
    call_first = floor.may_open(state, channel=Channel.CALL)
    _show(clock, f"  通话里安静 5 秒：{call_first.allowed} / {call_first.reason}")
    assert call_first.allowed
    floor.note_opened(state, channel=Channel.CALL)
    _show(clock, f"  她开口：连续 {state.streak} 次（通话档不动文字端的标记）")
    assert state.streak == 1 and not state.text_fired

    clock.advance(9)
    call_second = floor.may_open(state, channel=Channel.CALL)
    _show(clock, f"  他没回话，又安静 9 秒：{call_second.allowed} / {call_second.reason}"
                 f"（间隔闸 8 秒）")
    assert call_second.allowed
    floor.note_opened(state, channel=Channel.CALL)
    _show(clock, f"  连续开口 {state.streak} 次 —— 到上限了。")

    clock.advance(60)
    tired = floor.may_open(state, channel=Channel.CALL)
    _show(clock, f"  再等 60 秒：{tired.allowed} / {tired.reason}（终局：等他开口）")
    _show(clock, f"  这时候的布防：{floor.arm_after(state, channel=Channel.CALL)}")
    assert not tired.allowed and tired.reason == "max_streak"
    assert floor.arm_after(state, channel=Channel.CALL) is None

    _show(clock, "出稿闸再看三句：")
    _show(clock, f"  「你好」→ {floor.line_rejected(state, '你好')}")
    _show(clock, f"  「那今晚早点睡，别又熬到三点。」→ "
                 f"{floor.line_rejected(state, '那今晚早点睡，别又熬到三点。')}（重复）")
    _show(clock, f"  「你怎么不理我」→ {floor.line_rejected(state, '你怎么不理我')}（禁用句）")

    _show(clock, "他刷新了页面（状态落盘再读回来）：")
    state = State.from_dict(json.loads(json.dumps(state.to_dict(), ensure_ascii=False)))
    _show(clock, f"  连续 {state.streak} 次还在，不因刷新重新布防。")
    assert state.streak == 2
    floor.note_user_spoke(state)
    _show(clock, f"  他一开口，全部清零，布防："
                 f"{floor.arm_after(state, channel=Channel.TEXT):.0f} 秒")

    print("状态机跑完一遍：判定只读、note_* 才写，刷新不会把用掉的机会还回去。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
