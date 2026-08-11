# Augur 差异化策略

- **状态**：Product Strategy
- **撰写日期**：2026-08-12
- **前置文档**：[`COMPETITIVE_LANDSCAPE_SUPPLEMENT_2026-08-12.md`](research/COMPETITIVE_LANDSCAPE_SUPPLEMENT_2026-08-12.md)、[`PRODUCT_DIRECTIONS.md`](PRODUCT_DIRECTIONS.md)、[`FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md`](research/FINANCIAL_PLATFORM_AGENT_SKILL_BENCHMARK_2026-08-11.md)
- **适用**：v11 RC 产品定位、messaging、功能优先级决策

## 一句话差异化

> **Augur 是唯一同时拥有 18 个投资哲学镜头、point-in-time 证据账本、可复验运行记录和完整本地运行时的 research memory system。**

竞品要么有视角无证据（AI Berkshire），要么有证据无视角（Mira），要么有数据无 product surface（OpenBB）。Augur 把它们放在一个 local-first 的产品里。

---

## 一、定位：从 "Multi-Agent 投研" 到 "Research Memory System"

### 问题

当前 Augur 的外部感知可能是"又一个 AI 股票分析工具"或"18 个大师帮你炒股"。这两个定位都有问题：

- "AI 股票分析"赛道拥挤（TradingAgents、ai-hedge-fund、Dexter 都在这里），且用户期望的是"推荐牛股"而非"研究工具"
- "18 个大师"听起来像算命，且 18 个并列输出无法形成决策信号

### 重新定位

```
不是 "AI 帮你分析股票"  →  而是 "你的研究记忆系统"
不是 "18 个大师给分数"  →  而是 "18 个镜头帮你发现盲点"
不是 "生成一份报告"      →  而是 "记住什么变了、谁的观点被证伪"
```

### 建议的产品一句话

> **Augur is a local-first research memory system for earnings-driven investors. It tracks what you knew, when you knew it, what changed, who disagrees and why — across quarters.**

对应中文：
> **Augur 是面向财报驱动型投资者的本地研究记忆系统。记录你何时知道什么、什么变了、谁在什么事实上分歧、以及为什么。**

### Messaging 金字塔

```
Layer 1: "从 ticker list 到有据可查的研究 dossier，<10 分钟"（北极星指标）
Layer 2: "缺失数据不会冒充事实；每个结论可追溯到 SEC filing 原文"
Layer 3: "18 个投资哲学镜头帮你发现共识里的盲点"
Layer 4: "跨季度追踪：guidance 变了、内部人卖了、某大师沉默了——这些都是信号"
Layer 5: "开源的、本地的、你的数据留在你的机器上"
```

---

## 二、竞品差异化矩阵

| 能力维度 | Augur | Mira | AI Berkshire | FinSight-AI | AlphaAnalyst | OpenBB |
|---|---|---|---|---|---|---|
| **自有 Runtime** (CLI+Dash+MCP) | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Local-first** | ✅ | ✅ | ✅ | ❌ (需PG/Redis/RabbitMQ) | ❌ (需PG/Redis) | ❌ (cloud-first) |
| **Persona 多视角** | ✅ 18个 | ❌ | ✅ 4个大师 | ❌ | ❌ | ❌ |
| **Point-in-time evidence** | ✅ (计划中) | ⚠️ refresh boundary | ❌ | ⚠️ snapshot hash | ❌ | ❌ |
| **Thesis 追踪** | ✅ (计划中) | ✅ thesis system | ✅ thesis-tracker/drift | ❌ | ❌ | ❌ |
| **跨季度变化账本** | ✅ (计划中) | ⚠️ event delta | ✅ thesis-drift | ❌ | ❌ | ❌ |
| **Filing delta** | ✅ (计划中) | ❌ | ⚠️ earnings-review | ❌ | ❌ | ❌ |
| **Evidence ledger** | ✅ (计划中) | ✅ evidence log | ❌ | ✅ evidence trace | ✅ citation validator | ❌ |
| **OOS 评估/Replay** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **MCP Resources** | ✅ (计划中) | ❌ | ❌ | ❌ | ❌ | ✅ tools |
| **中文支持** | ✅ | ✅ | ✅ | ✅ (A-share) | ❌ | ⚠️ |

### 解读

1. **没有人同时拥有 Persona + Evidence + OOS Replay**。这是 Augur 的第一道护城河。

2. **Local-first + 完整 Runtime** 是第二道护城河。Mira 和 AI Berkshire 依赖 Claude Code/Codex，Augur 可以独立运行。

3. **跨季度变化追踪**（thesis delta、filing delta、guidance tracker）目前是所有竞品的弱项。Mira 的 event delta 最接近但仍在早期；AI Berkshire 的 thesis-drift 是 prompt 驱动而非结构化。这是 Augur 可以抢先建立的第三道护城河。

4. **中文市场**：AI Berkshire 面向中文用户但专注港股/中概；FinSight-AI 限定 A-share；Augur 面向 US 公开市场但有完整中文支持——这是独特的交叉定位。

---

## 三、Persona 差异化：从并列到对抗

### 现状问题

Augur 的 18 Persona 当前是"并列输出"——每个大师独立打分，然后取平均或加权。这导致：
- 用户看到的是 18 份大同小异的报告
- 真正有价值的分歧被平均值稀释
- "18"这个数字本身就是信息过载

### 建议：升级为 "Structured Disagreement Map"

借鉴 AI Berkshire 的四大师对抗设计，但用 Augur 的 18 Persona + Evidence 做得更系统：

**产品设计**：
```
不是：18 个并列表格（每人一行，各自打分）
而是：按 claim 对齐的争议视图（每个关键事实，谁 bullish / bearish / abstain / 各有什么证据）

不是：取平均分 = consensus
而是：展示共识强度（几人 agree、几人 dissent、几人 silent），沉默本身就是信号

不是：committee 辩论是"多写一段摘要"
而是：只对有争议的 claim 进行 evidence-seeking re-query
```

**具体展现**：

| Claim | 事实 | Bullish (证据) | Bearish (证据) | Abstain (原因) |
|---|---|---|---|---|
| "护城河在扩大" | 毛利率连续3年 >60% | Buffett, Munger (10-K p45) | Thiel (竞争加速) | Li Lu (数据不足) |
| "管理层可信" | CEO 持股 >10%、无 insider selling | Buffett, Fisher, Lynch | Soros (过度乐观 guidance) | — |

**18→3 压缩**：
- 18 个 Persona 在后台运行，但产品只展示 3-5 个**决策相关冲突**
- 沉默的大多数显示为 "N persona have no strong view on this claim"
- 用户永远可以展开看全部 18 个

---

## 四、Thesis 差异化：从 "报告" 到 "记忆"

### 现状问题

目前的 Augur 产出是一次性报告。用户跑完 → 看完 → 关掉。没有"回来"的理由。

### 建议：打造 Research Memory 体验

借鉴 Mira 的 thesis system + AI Berkshire 的 thesis-tracker，但在 Augur 的 runtime 中实现：

**核心产品循环**：

```
1. 用户为 AAPL 创建 thesis："Apple 的 services revenue 将在 2 年内超过硬件"
2. Augur 自动关联：哪些 Persona 支持/反对这个 thesis、哪些 evidence 相关
3. 每次财报后，Augur 生成 "Thesis Delta"：
   - 事实变化：services revenue 占比从 26% → 28%
   - 估值变化：PE 从 28x → 25x
   - 措辞变化：guidance 从 "strong growth" → "moderate growth"
   - 证伪条件检查：services growth <15% → thesis weakened
4. 用户标记 intact / weakened / refuted
5. 6 个月后回头看：当时为什么相信这个 thesis？什么证据让我改变看法？
```

这比 Mira 的 thesis system 多了 **Persona 视角**（不只追踪事实，还追踪谁对谁错），比 AI Berkshire 多了 **structured runtime**（不依赖 Claude Code conversation）。

---

## 五、技术差异化：Information-Time vs. Retrieval-Time

### 这是 Augur 最深的护城河

几乎所有竞品（包括 Mira、AI Berkshire、FinSight-AI）都在用 `retrieved_at`（数据获取时间）代替 `available_at`（市场可获得时间）。这意味着：

- 回测时可能用了未来数据
- "X 机构在 Q1 增持"这个信息出现在 13F 披露前就参与了分析
- look-ahead bias 被静默引入

Augur 的 `EvidenceItem` schema 定义了三类时间：

```
effective_at    → 事实对应的业务时点（Q4 earnings 的 fiscal period end）
available_at    → 市场最早能获得该信息的时间（13F 在 quarter end +45 days）
retrieved_at    → 系统实际获取时间（何时从 SEC 下载）
```

**这是 Augur 唯一可以声称"我们做得比所有人都更正确"的维度。** 如果 v11 把 `available_at` 做实，Augur 就拥有了所有竞品都没有的可信度底座。

必须做的：
- 所有历史 replay 中 100% evidence 有 `available_at` 或显式 `unknown`
- `available_at` 不得用 `retrieved_at` 替代
- 13F 的 `available_at` = quarter end + 45 days（不是 filing date）
- 对于无法确知 available_at 的历史数据，标记为 `unknown` 并降级

---

## 六、产品形态差异化：Runtime 即壁垒

Mira 和 AI Berkshire 的成功恰恰证明了"Skills 仓库"模式的天花板——它们依赖 Claude Code/Codex，用户体验受限于这些客户端的交互模式。

Augur 拥有：
- **CLI**：适合 batch、cron、脚本化工作流
- **Dashboard**：适合浏览、探索、视觉对比
- **MCP**：适合作为外部 Agent 的 evidence provider
- **Bots**：适合推送关键事件变化

这不是"三个界面"，是三种不同的信息消费模式——大部分竞品只有其中一个。

---

## 七、不做什么（差异化就是取舍）

| 竞品在做的事 | Augur 为什么不做 |
|---|---|
| 全量全球数据（FinChat） | 聚焦 US 公开市场 + EDGAR，质量 > 广度 |
| 自然语言回答一切（OctagonAI） | 结构化 output > 聊天式 answer，可复验 > 可读 |
| 多 Agent 数量竞赛（TradingAgents） | 18 个够了。做好对抗比加第 19 个有用 |
| DCF/估值计算（AlphaAnalyst） | 留在 P4 邻接方向。先做实证据链再碰估值 |
| Portfolio tracking / broker sync | 明确 killing。这不是投研工具的核心 |
| 社交/Marketplace（Agent Skills） | 至少一个外部贡献者通过安全门后再说 |
| 移动端、SaaS、计费 | 至少 5 位用户连续两个财报周期后再考虑 |

---

## 八、差异化落地路线

### v11 RC（本周）——建立 Trust Moat

| 优先级 | 能力 | 为什么是差异化 |
|---|---|---|
| P0 | `available_at` 做实 | 所有竞品都没做对 |
| P0 | missingness 显式传播 | 所有竞品都静默填 0 |
| P0 | RunBundle 不可变 | 唯一可复验的投研工具 |
| P1 | 两个内置 Skill | 为 Thesis/Delta 打地基 |

### v11.1（下一周）——建立 Product Moat

| 优先级 | 能力 | 为什么是差异化 |
|---|---|---|
| P0 | Structured Disagreement Map | Persona 从 18 个名字变成 3 个冲突 |
| P0 | Thesis Journal + Thesis Delta | 从 "生成报告" 变成 "研究记忆" |
| P1 | Earnings Queue + Pre/Post Dossier | 财报事件闭环 |
| P1 | Refresh boundary（Mira 概念） | 告诉用户什么结论需要重新验证 |

### v11.2+ ——建立 Evaluation Moat

| 优先级 | 能力 | 为什么是差异化 |
|---|---|---|
| P1 | Thesis outcome tracking | 谁对了、谁错了、为什么 |
| P1 | Persona OOS evaluation | 不用嘴说谁厉害，用 replay 证明 |
| P2 | Public Research Evidence Pack | 发布可引用的证据包 |

---

## 九、每个新功能必须回答的五个问题

（继承自 PRODUCT_DIRECTIONS.md，补充差异化视角）

1. 它是否缩短 watchlist 到有效 dossier 的时间？
2. 它是否让来源、时点、缺失项或变化更清楚？
3. 它是否增加下一次财报周期的回访理由？
4. 它是否复用统一事件、证据和 run bundle？
5. **如果竞品要做，他们需要多久？** （新增加——差异化检验）

能超过竞品 6 个月以上的能力优先投入；会被竞品 1 个月内追平的作为防御性开发；与竞品同质化的降级或暂停。
