# 宿主接法（integration）

这份文档是给宿主作者的：怎么把 huatou 接进一条真实的流水线。每一节回答一个
「不这么做会怎样」—— 判据本身的来源在 [`rules.md`](rules.md)，边界在 [`design.md`](design.md)。

## §1 一张图：五个调用点

```
用户消息进来 ──note_user_spoke────────────────────────────────────────┐
                                                                    │
页面打开 / 一个回合收尾 ──arm_after(state, channel) ──► 挂表 … 定时器到点
                                                                    │
                                      主动请求到达 ──may_open(state, channel)
                                                                    │
                                                   放行 → 出稿 → line_rejected(第一句)
                                                                    │
                                      真的发出去了 ──note_opened───┘
                                                     note_said / note_her_ask

用户消息进来（答她）── note_user_spoke ＋ 出稿前 should_hand_back(state, user_msg)
```

两条分工贯穿全库，接错任何一条都会把状态弄成两处真源：

- **判定只读**：`may_open` / `should_hand_back` / `arm_after` / `line_rejected` /
  `must_wait` / `asks_the_user` 一个字节都不写。它们可以随便调用、随便打日志、
  随便在面板上跑。
- **改写只有 `note_*`**：`note_user_spoke` / `note_opened` / `note_said` /
  `note_her_ask` 是仅有的入口。宿主调错一次（比如「放行但最终没发出去」也调了
  `note_opened`），症状是「她少说了一句」，而日志上什么都看不出来。

