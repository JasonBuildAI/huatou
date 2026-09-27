# huatou（话头）

**一个只回答「这一句该不该由她说出口」的发言权管理器。**

它不生成内容、不合成、不播放、不检索；它把「什么时候可以开口、答完要不要把话头递回去、
递了之后等不等、这句话能不能出口」从产品代码里的 if 堆，变成一个可注入时钟与随机数、
可被假时钟测穿、状态可持久化的策略对象。

四层里的位置：

```
changqing   我记得什么           （记忆）
huatou      我什么时候说、说什么   （决策）  ← 本仓库
echoturn    我怎么说出去          （表达）
touchstone  我怎么知道它变好了     （验收）
```

设计真源是 [`docs/design.md`](docs/design.md)：每一节都尽量回答「不这么做会怎样」，
凡是数字都写明它在源系统里是怎么被量出来的。

## 现在到哪一步

判据全部落地，每一条都是「代码 + 一条能失败的测试 + docs 里的理由」三件套：

- [`docs/design.md`](docs/design.md)：设计真源，每一节都回答「不这么做会怎样」；
- [`docs/rules.md`](docs/rules.md)：逐条判据表，带源材料行号与真机证据日期；
- [`docs/integration.md`](docs/integration.md)：宿主怎么接 —— 布防、还机会、
  刷新继承，与四个 `note_*` 的调用点。

## 怎么跑

三条验收命令（`docs/design.md` §8）：

```powershell
python -m pytest            # 默认档：全绿，且断网可跑（元档不选中）
python -m pytest -m meta    # 元档：把实现改坏一点，证明默认档真的会红
python -m huatou demo       # 跑一遍假宿主的完整状态机（examples/companion.py）
```

再加一条反证：**把 `huatou/opening.py` 里任意一道判据注释掉，`python -m pytest`
必须变红**（`docs/design.md` §8 的第二条硬验收）。这条红不了，说明那一档
没有能失败的用例在看着它。

## 目录

```
huatou/     # 库本身：types / dials / protocols / ask / opening / handback / lines / floor
tests/      # 默认档 + 元档（test_meta.py）+ 隐私护栏（test_privacy.py）
docs/       # design.md 设计真源 / rules.md 判据表 / integration.md 宿主接法
examples/   # companion.py 假宿主示范（python -m huatou demo 跑的就是它）
```

## 三条立库时的约定

- 核心零第三方依赖：`import huatou` 不许把任何非标准库模块带进 `sys.modules`。
- 阈值只有一张表（`Dials`），**调用时现读**，不在导入期快照成模块常量。
- 判定是纯函数、只读状态；改写状态只有 `note_*` 三个入口。