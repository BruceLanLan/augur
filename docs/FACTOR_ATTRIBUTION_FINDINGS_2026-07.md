# 因子归因真实数据发现（2026-07-14）

**性质**：`scripts/factor_attribution.py`（B2）与 `scripts/generate_rolling_ic.py`（B1）在同一个 37 支股票、2022-01～2026-06 真实窗口上的完整跑批结果记录。两个结论都过了 split-half（或等价的分regime加权）稳定性检验，但**只代表这一个窗口的观察，不是可以直接下注的结论**——读下面"如何解读"一节再用。

---

## 一、rolling IC（B1）：18 位大师整体横截面 IC 全部挤在接近零的窄带里

真实运行 `generate_rolling_ic.py`（37 票，1106 个合格交易日，39816 条时点记录）后，18 位大师的整体 IC 从最高 `marks`/`soros` 的 **+0.001** 到最低 `fisher` 的 **-0.062**，跨度只有 0.063。

**判断**：这个跨度太窄，大概率落在噪声范围内——不像 R5 的 pairwise 相关性矩阵那样有清晰的高相关对（>0.7），也不像下面 B2 的因子发现那样有稳定的方向性。`feedback/rolling_ic.json` 已经生成并提交（commit `cef73d1`），这会让 `engine.py` 里那段一直空转的 50/50 混合逻辑开始真正生效——但生效不等于验证过有效。这和 regime 权重当年的处境很像：先激活，再看数据说话。**建议**：找时间给 rolling IC 也补一次 `regime_weight_oos.py` 那种前后对比的 OOS 验证（"开这个混合 vs 不开，横截面 IC 有没有差别"），再决定要不要保留。

## 二、因子级归因（B2）：护城河/质量类因子在这个窗口里持续跑输

`factor_attribution.py` 全量运行（同样 37 票、1106 天，38710 条记录，其中 PG/WMT 因 yfinance 临时问题返回 0 条，其余 35 支都完整）找到 86 个具名因子，其中 **24 个通过了 split-half 稳定性检验**。这 24 个里几乎清一色是"护城河 / 质量 / 品牌 / 管理层"这类因子，且**全部是负 IC**（前后两段窗口方向一致）：

| 因子 | 整体 IC | 前半段 | 后半段 |
|------|---------|--------|--------|
| thiel.monopoly_power | -0.0640 | -0.0641 | -0.0639 |
| dan_bin.brand_moat | -0.0622 | -0.0578 | -0.0666 |
| duan_yongping.moat_quality | -0.0595 | -0.0300 | -0.0890 |
| li_lu.competitive_position | -0.0589 | -0.0485 | -0.0692 |
| zhang_lei.business_model_quality | -0.0566 | -0.0373 | -0.0759 |
| buffett.moat | -0.0557 | -0.0584 | -0.0529 |
| ...（完整 24 条见运行输出，或重新跑脚本） | | | |
| dayu.information_edge | +0.0300 | +0.0235 | +0.0365 |（唯一一个正向且稳定的）

**如何解读**：护城河/质量类因子偏向给"已经很贵、已经很知名"的大盘股打高分（AAPL/MSFT/KO/PG 这类）。2022-2026 这个窗口恰好包含了 2022 年加息周期对成长/质量股的重创，以及能源、金融等价值/周期股在部分年份的强势——"质量因子跑输"在这类宏观背景下是有经济学解释的，不是明显的计算错误。但这仍然只是**一个 4.5 年窗口的观察**，跟 regime_weight_oos.py 反复强调的纪律一样：不要把"这一段历史里跑输"直接推广成"护城河因子没用"这种一般性结论，尤其是这个窗口本身可能被 1-2 个宏观周期主导（加息、AI 叙事等），不是独立样本的集合。

## 三、意外发现：回放管道从不填充 insider_ownership / institutional_ownership

在核对"为什么 `li_lu.management_quality` 和 `zhang_lei.management_excellence` 的 IC 数字精确到小数点后四位完全相同"时，定位到一个真实的、影响范围更广的基础设施缺口：

`fetch_ticker_replay_records`（`src/augur/backtest.py`）构建的历史回放记录**从未包含 `insider_ownership` / `institutional_ownership` 字段**——这两个字段在每一次历史回放构造的 `MarketContext` 里都停留在 dataclass 默认值 0。原因是持股比例的**历史时间序列**本身没有免费数据源（这跟已经记录在案的 `insider_buying_signal`/`institutional_flow_signal`——追踪的是*交易行为*而不是*持股比例*，且同样没接入 persona 的 factors——是两个不同但同类的缺口）。

**影响范围**：11 位大师的因子公式依赖这两个字段（`aschenbrenner`、`buffett`、`dan_bin`、`dayu`、`duan_yongping`、`fisher`、`li_lu`、`marks`、`munger`、`thiel`、`zhang_lei`），这意味着**所有基于历史回放的分析**——不只是这次的 B1/B2，还包括已经上线的 `regime_weight_oos.py` 和 R5 的 `generate_agent_correlation.py`——在计算这些大师的相关因子/信号时，持股比例部分实际上是被静默清零的。具体到这次的观察：`li_lu.management_quality` 和 `zhang_lei.management_excellence` 两条公式在清零持股比例字段后都退化成"只是 ROE 的单调阶梯函数"，而 Spearman 秩相关只看排序不看数值——两个对同一变量做单调变换的函数,排序必然完全一致，所以两条 IC 曲线才会逐日、逐位小数都相同。这不是巧合命中，也不是两个因子互相独立验证了同一个结论，而是这个数据缺口造出来的假象。

**判断**：这不是这次要修的 bug——历史持股比例数据本身就没有免费来源，修不了。但值得记录下来，避免以后有人拿"两个不同大师的因子 IC 完全一致"当成真实发现来解读。代码里已经在 `_record_to_market_context`（`src/augur/backtest.py`）加了对应注释。

---

## 四、给下次分析的建议

- 如果要认真验证"质量因子跑输"这个发现是否稳健，下一步是像 `regime_weight_oos.py` 对 2018-2020 窗口做的那样，换一个不同宏观周期的窗口重跑一次，看方向是否还成立（B3 已经在头脑风暴清单里，可以跟这个合并考虑）。
- rolling IC 的整体 IC 跨度太窄，不建议在没有做 OOS 前后对比之前，把 `feedback/rolling_ic.json` 已生效这件事当成"共识质量变好了"的证据。
- insider_ownership/institutional_ownership 缺口目前无法绕过（没有免费历史数据源），但如果未来找到付费/其他数据源，`aschenbrenner`/`buffett`/`dan_bin`/`dayu`/`duan_yongping`/`fisher`/`li_lu`/`marks`/`munger`/`thiel`/`zhang_lei` 这 11 位大师的相关因子会是直接受益方。
