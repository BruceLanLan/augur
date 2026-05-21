# Hermes Web UI 整合计划

> 将 augur 的投资人人格分析系统作为 Hermes Web UI 的功能模块
> 参考项目：https://github.com/EKKOLearnAI/hermes-web-ui

---

## 一、Hermes Web UI 项目概况

| 维度 | 信息 |
|------|------|
| 技术栈 | Node.js/TypeScript + React + Vite |
| 后端 | Express + Socket.IO + Hermes Agent Bridge |
| 数据库 | SQLite (sessions, config, kanban) |
| 通信 | Socket.IO `/chat-run` 实时流式传输 |
| UI框架 | 自建React组件库 |
| 安装 | `npm install -g hermes-web-ui && hermes-web-ui start` |
| License | MIT |

### 已有的核心功能
- AI Chat 会话管理（多会话、Socket.IO 流式）
- Platform Channels 配置（8个平台）
- Cron Job 调度管理
- Skills 浏览/搜索/安装
- Usage & Cost 监控
- 模型/Provider 切换

---

## 二、三种整合方案

### 方案 A：Hermes Agent Skill 模式 🏆 推荐
**难度**: ⭐（1天）
**工作量**: 最小
**用户心智负担**: 最低

直接通过 Hermes Agent 的 Skill 系统整合：
1. augur 已自带 SKILL.md（已完善的 Hermes Skill 格式）
2. 用户在 Hermes Web UI 中通过聊天调用：
   - `/skill augur` 加载技能
   - 或 `hermes skills install <url>` 安装
3. 通过自然语言交互：`分析苹果AAPL，使用巴菲特人格`
4. 所有 Agent 分析在后台运行，结果流式返回

**优点**：无需改一行 hermes-web-ui 代码，利用现有 Agent Bridge

### 方案 B：独立 FastAPI Web + iframe 嵌入
**难度**: ⭐⭐（3天）
**工作量**: 中等
**用户心智负担**: 中

1. augur 已有 FastAPI dashboard（`dashboard/app.py`）
2. 完善为独立服务（添加 CORS、API 端点等）
3. 在 Hermes Web UI 中通过 iframe 嵌入
4. 需要 hermes-web-ui 支持 iframe 嵌入路由

**优点**：功能完整、UI可控、高速交互
**缺点**：两个后端服务，增加部署复杂度

### 方案 C：正式 PR 到 hermes-web-ui 🌟
**难度**: ⭐⭐⭐（1-2周）
**工作量**: 大
**用户心智负担**: 最低（原生体验）

1. 在 hermes-web-ui 中添加 "Investment Analysis" 页面
2. 使用其 React 组件库（复用 chat 会话、数据表格等）
3. 后端通过 Hermes Agent Bridge (`/chat-run`) 调用分析
4. 前端展示 Agent 评分雷达图、多Agent对比、时间线等

**优点**：原生体验、可集成到导航栏
**缺点**：需合作双方协调PR

---

## 三、推荐实施路线

```
Phase 1: Skill 封装 ✅（已完成）
  └─ augur/SKILL.md 已完善
  
Phase 2: Skill 发布
  ├─ 发布到 Hermes Skills Hub
  └─ 用户：hermes skills install augur

Phase 3: 独立 Web UI 增强
  ├─ 完善 FastAPI dashboard（正在做）
  ├─ 添加 CORS 支持
  └─ 可选：nginx 反向代理 / Docker 部署

Phase 4: PR 到 hermes-web-ui
  ├─ 联系 ekko 团队
  ├─ 提交 Investment Analysis 页面 PR
  └─ 联合宣传发布
```

---

## 四、关键 API 接口

### augur API（FastAPI）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Dashboard 首页 |
| `/personas` | GET | 投资人人格列表 |
| `/api/analyze/{ticker}` | GET | 单标的分析 |
| `/api/persona/{id}/evolution` | GET | 人格进化时间线 |
| `/api/consensus/{ticker}` | GET | 多Agent共识 |

### Hermes Agent Bridge API（供Web UI调用）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/chat-run` | Socket.IO | 聊天运行（流式） |
| `/api/skills` | GET | 技能列表 |
| `/api/skills/:name/load` | POST | 加载技能 |

---

## 五、PR 准备清单

- [x] SKILL.md 格式正确
- [x] 人格系统完整（12位投资人）
- [x] 大宇人格已加入
- [x] 人格进化追踪系统
- [ ] FastAPI dashboard 完善 CORS
- [ ] 添加 REST API 端点
- [ ] Docker 容器化
- [ ] 与 hermes-web-ui 团队沟通PR
- [ ] 确定前端组件方案（React/独立）

---

## 六、长期愿景

**目标**: 成为用户本地的每日金融终端（Daily Financial Terminal）

```
Daily Financial Terminal（日常金融终端）
├── 人格分析系统（12位投资大师）
├── 自建数据仓库（价格/基本面/宏观）
├── 实时预测追踪
├── 组合风险管理（Kelly/Calmar/VaR）
├── 自动日报推送（Cron）
├── Hermes Web UI 集成
└── 社区技能插件
```

## 六、未来工作计划（TODO — 下一个Agent注意）

以下事项已记录到内存，但尚未完成，下一个接手的Agent请优先处理：

### P0 — 持仓数据精准化
当前所有12位投资人的 `current_portfolio_themes` 是通用描述，需要基于真实数据更新：
- **Buffett**: 从 Berkshire Hathaway 最新的 SEC 13F filing 获取精确持仓（2026 Q1: 26只股票，$263B）
- **Aschenbrenner**: 公开的AI持仓（英伟达、微软、ASML等）
- **Cathie Wood**: ARK Invest 每日披露的持仓
- **其他**: 参考各自最新的公开报告/13F

### P1 — 新增投资人Personas
| 优先级 | 投资人 | 风格 | 原因 |
|--------|--------|------|------|
| 🔴 | **段永平 (Duan Yongping)** | 价值+重仓+现金流 | 用户明确提及，大宇引用的偶像 |
| 🟡 | 张磊（高瓴资本） | 长期结构性价值 | 中国顶级投资人 |
| 🟡 | 李录（喜马拉雅资本） | 中国价值投资实践 | 巴菲特门徒，中国实践 |
| 🟢 | 但斌（东方港湾） | 消费+科技成长 | 中国知名私募 |
| 🟢 | Michael Burry | 深度价值+做空 | Scion Asset Management |
| 🟢 | Bill Ackman | 积极主义投资 | Pershing Square |

### P2 — Hermes Web UI PR整合
- 联系 EKKOLearnAI 项目创始人（用户熟人）
- 在 hermes-web-ui 中添加 Investment Analysis 原生页面
- 后端通过 Hermes Agent Bridge 调用分析

### P3 — 功能迭代
- private版 (agent-personas-dev) 的算法/数据仓库逐步合并回 public 版
- Docker 容器化
- 日频数据仓库支持

---

*最后更新: 2026-05-21*
*注意: 以上内容已写入系统内存，切换Agent时请用 session_search("未来工作计划") 查看*
