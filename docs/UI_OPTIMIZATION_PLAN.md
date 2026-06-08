# Augur v9 — UI 优化计划

> 基于当前 v9.0.8 的 Dashboard 现状，按优先级列出可执行的 UI 改进任务。
> 每项均含：**目标页面 / 文件、具体改动、验收标准**。

---

## P0 — 视觉一致性（最优先，影响整体质感）

### 1. CSS Token 去重统一

**问题：** `bloomberg.css` 和 `colors_and_type.css` 各自定义了一套 CSS 变量，存在同名但值不同的变量（如 `--bg-card`、`--border-color`）。bloomberg.css 的变量覆盖了 colors_and_type.css，导致样式难以维护。

**目标文件：**
- `dashboard/static/css/bloomberg.css`（:root 部分，约第 7-50 行）
- `dashboard/static/css/colors_and_type.css`

**具体改动：**
- 审计两份文件的重复变量，以 `colors_and_type.css` 为 single source of truth
- bloomberg.css 删除所有与 colors_and_type.css 重复的 `:root` 变量声明
- bloomberg.css 中直接引用语义 token（如 `var(--signal-buy)` 而非硬编码 `#00c853`）

**验收：** 全局搜索硬编码颜色 `#00c853`、`#ff1744`、`#ffd600`、`#ff8c00` 数量减少 90%+。

---

### 2. Chart.js 主题统一

**问题：** compare 雷达图和 stocks 折线图的 Chart.js 配色是在 JS 里硬编码的（`#ff9500`、`#30d158` 等），与 CSS token 脱钩，亮色模式下看不清。

**目标文件：**
- `dashboard/templates/compare.html`（`renderRadarChart` 函数）
- `dashboard/templates/stocks.html`（`loadHistoryChart` 函数）

**具体改动：**
```javascript
// 统一从 CSS 变量读取颜色
function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
// 使用：
var gridColor = getCssVar('--border-color') || 'rgba(255,255,255,0.08)';
var labelColor = getCssVar('--text-muted') || '#636366';
var buyColor = getCssVar('--signal-buy') || '#00c853';
var sellColor = getCssVar('--signal-sell') || '#ff1744';
```
- Chart.js `scales.r.grid.color`、`ticks.color`、`pointLabels.color` 全部改为读 CSS 变量
- 雷达图 PALETTE 改为从 CSS 变量动态生成（5 种语义色：accent-orange、signal-buy、accent-blue、accent-purple、signal-sell）

**验收：** 切换 Light/Dark 模式后，图表颜色随之切换，无白底看不清问题。

---

### 3. 亮色模式（Light Mode）完整性

**问题：** 部分组件在 Light 模式下颜色异常（文字不可见、背景叠色）。主要集中在：
- Committee 页 `.opinion-card` 边框
- Compare 页雷达图背景
- Streaming progress bar 在 light 下不可见

**目标文件：** `bloomberg.css`（html.light 区块）+ `committee.html`、`compare.html` 的内联 style

**具体改动：**
- 检查并补充 `html.light` 下的 `.opinion-card`、`.verdict-panel`、`#compare-radar-container` 覆写
- 将所有 `background: rgba(255,255,255,0.08)` 类的半透明值改为 CSS 变量

---

## P1 — 新功能页面打磨（委员会、对比）

### 4. 委员会流式卡片动画强化

**目标文件：** `dashboard/templates/committee.html`

**当前状态：** 每张 opinion-card 有 `animation: opinion-in 0.22s ease`，但卡片之间没有延迟错位感。

**具体改动：**
```css
/* 让卡片依次出现，有层次感 */
.opinion-card:nth-child(1) { animation-delay: 0s; }
.opinion-card:nth-child(2) { animation-delay: 0.05s; }
/* ...或在 JS 里用 setTimeout 添加 */
```
- `renderStreamingOpinion` 函数中，给 card 添加 `style="animation-delay: ${index * 0.04}s"`
- 进度条颜色根据当前大师信号变色：bullish → 绿色，bearish → 红色，neutral → 黄色

**验收：** 流式渲染时卡片有层次感，不是同时闪现。

---

### 5. 委员会 Verdict 揭幕动画

**目标文件：** `dashboard/templates/committee.html`

**具体改动：**
- `#committee-results` 从 `display:none` 变为可见时，加 `opacity 0→1` + `translateY 12px→0` 过渡
- Verdict panel 的 4 个数字（Signal / Score / Confidence / Kelly）用 `countUp` 效果（简单实现：requestAnimationFrame 从 0 数到目标值，约 600ms）

```javascript
function animateNumber(el, target, decimals, suffix) {
    var start = 0, dur = 600, startTime = null;
    function step(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / dur, 1);
        el.textContent = (start + (target - start) * progress).toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}
```

**验收：** Verdict 数字从 0 动画到最终值，整体揭幕有仪式感。

---

### 6. Compare 雷达图响应式

**目标文件：** `dashboard/templates/compare.html`

**当前状态：** `max-width: 480px` 在移动端正常，但在宽屏（>1200px）时雷达图显得太小，与下方卡片列表比例失衡。

**具体改动：**
```css
#compare-radar-container {
    max-width: min(480px, 100%);
    /* 宽屏时居中并适当放大 */
}
@media (min-width: 1200px) {
    #compare-radar-container {
        max-width: 560px;
    }
}
```
- 雷达图标题改为显示 ticker 名：`${ticker} — 评分雷达图`
- 在雷达图下方加一行说明文字（小字，text-muted）：`各维度均换算为 0-10 分；论据量 / 风险意识按条目数等比缩放`

**验收：** 在 375px / 768px / 1440px 三个宽度下雷达图均清晰可用。

---

### 7. Compare 卡片信号色标注强化

**目标文件：** `dashboard/templates/compare.html`

**当前状态：** agree/disagree 只用边框颜色区分，不够直观。

**具体改动：**
- agree 卡片左上角加一个小绿点 `●`（`color: var(--signal-buy); font-size: 8px`）
- disagree 卡片左上角加红点
- 无明确多数时不显示
- 在卡片右下角加 confidence 进度条（细线，宽度 = confidence%）：

```html
<div style="height:2px; background:var(--border-color); border-radius:1px; margin-top:8px;">
    <div style="height:100%; width:{confidence*100}%; background:var(--accent-orange); border-radius:1px;"></div>
</div>
```

---

## P2 — 首页 & 导航提升

### 8. Ticker Tape 暂停 UX

**目标文件：** `dashboard/templates/index.html`（ticker tape 相关代码）

**当前状态：** 支持暂停但没有视觉反馈，用户不知道是否已暂停。

**具体改动：**
- 暂停时 tape 上方显示一个小 badge：`⏸ 已暂停，点击继续`（`position: absolute; top: 2px; right: 8px`）
- 鼠标悬停时整个 tape 区域加淡淡的 overlay，提示"悬停已暂停"

---

### 9. 侧边栏激活态优化

**目标文件：** `dashboard/static/css/bloomberg.css`（sidebar nav 部分）

**当前状态：** 激活态只有 `border-left` 高亮，折叠后看不清。

**具体改动：**
- 激活态增加背景色：`background: rgba(255,140,0,0.08)`
- 折叠时激活图标加圆点标记（`::after` 小圆点，`background: var(--accent-orange)`）
- hover 时加 tooltip（`title` 属性），折叠模式下显示完整菜单名

---

### 10. 移动端底部导航完善

**目标文件：** `dashboard/static/css/bloomberg.css`（mobile nav 部分，约 1806px 断点）

**当前状态：** 移动端有底部导航，但超过 5 个 tab 时出现 overflow。

**具体改动：**
- 限制移动端底部导航最多显示 5 个最常用项：Dashboard / Stocks / Committee / History / Settings
- 其余页面通过侧边栏抽屉访问
- 当前激活的 tab 图标加上色 + 小数字 badge（若有未读历史）

---

## P3 — 数据可视化增强

### 11. Stocks 历史走势图交互

**目标文件：** `dashboard/templates/stocks.html`（`loadHistoryChart` 函数）

**当前状态：** 折线图可显示，但点击图上的历史点没有动作。

**具体改动：**
- Chart.js `onClick` 回调：点击某个历史分析点，在旁边展示那次分析的摘要（分析时间、评分、信号）
- 图表右上角加两个按钮：`30天 / 全部`，切换显示范围
- Y 轴范围固定为 `[0, 10]`，加参考线（水平虚线）：7.5=BUY threshold，2.5=SELL threshold

---

### 12. 首页 Scorecard 排名色阶

**目标文件：** `dashboard/templates/index.html`（scorecard grid 渲染部分）

**当前状态：** 18 位大师的评分卡颜色只按信号分三档（绿/黄/红）。

**具体改动：**
- 评分 > 8：深绿（`#00c853`）
- 评分 6-8：浅绿（`#69f0ae`）
- 评分 4-6：黄色（`#ffd600`）
- 评分 2-4：浅红（`#ff6e40`）
- 评分 < 2：深红（`#ff1744`）
- 评分数字字号随分值大小微变（8+ 时 font-size +2px，制造视觉层次）

---

## P4 — 性能与体验细节

### 13. 页面切换过渡动画

**目标文件：** `dashboard/static/css/bloomberg.css` + `base.html`

**具体改动：**
- 所有 `<main>` 内容区在路由切换时加 `opacity 0→1` 淡入（200ms）
- 实现方式：在 base.html 的 `<main>` 加 class，页面加载完成后移除 `page-entering` class
```css
.page-entering { opacity: 0; transform: translateY(4px); }
.app-main { transition: opacity 0.2s ease, transform 0.2s ease; }
```

---

### 14. Toast 通知系统升级

**目标文件：** `dashboard/static/js/` 或 `base.html` 的 toast 函数

**当前状态：** Toast 只有一种样式，没有 icon 区分。

**具体改动：**
- success：✓ 绿色左边框
- warning：⚠ 黄色左边框
- error：✗ 红色左边框
- info：ℹ 蓝色左边框
- 多条 toast 时垂直堆叠，不覆盖

---

### 15. 空状态（Empty State）插图统一

**目标文件：** 各页面的 empty state HTML

**当前状态：** empty state 用的是 emoji（📊 📈 等），风格与 HD-2D 像素风不搭。

**具体改动：**
- 统一改为 SVG 小插图（bloomberg terminal 风格线稿）
- 或改为像素风 ASCII art（更匹配游戏美学）
- 至少统一 3 个主要页面：history / watchlist / scanner

---

## 执行优先级总结

| 优先级 | 任务 | 工作量 | 影响面 |
|--------|------|--------|--------|
| P0 | CSS Token 去重 | 大 | 全局质感 |
| P0 | Chart.js 主题统一 | 中 | 所有图表 |
| P0 | Light Mode 修复 | 中 | 亮色用户 |
| P1 | 委员会动画强化 | 小 | committee 页 |
| P1 | Verdict 揭幕动画 | 小 | committee 页 |
| P1 | Compare 雷达响应式 | 小 | compare 页 |
| P1 | Compare 卡片标注 | 小 | compare 页 |
| P2 | Ticker Tape 暂停 UX | 小 | 首页 |
| P2 | 侧边栏激活态 | 小 | 全局导航 |
| P2 | 移动端底部导航 | 中 | 移动体验 |
| P3 | Stocks 图交互 | 中 | stocks 页 |
| P3 | Scorecard 色阶 | 小 | 首页 |
| P4 | 页面过渡动画 | 小 | 全局 |
| P4 | Toast 升级 | 小 | 全局 |
| P4 | Empty State 统一 | 中 | 3 个页面 |

**建议执行顺序：** P0（1→2→3）→ P1（4→5→6→7）→ P2 → P3 → P4

---

## 文件修改范围速查

```
dashboard/static/css/bloomberg.css        — P0/P2/P3/P4
dashboard/static/css/colors_and_type.css  — P0
dashboard/templates/committee.html        — P1
dashboard/templates/compare.html          — P1
dashboard/templates/stocks.html           — P3
dashboard/templates/index.html            — P2/P3
dashboard/templates/base.html             — P4
```
