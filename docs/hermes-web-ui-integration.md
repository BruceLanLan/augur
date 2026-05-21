# Hermes Web UI 整合计划

> 将 buffett-oracle-analyzer 的投资人人格分析系统作为 Hermes Web UI 的功能模块
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
1. buffett-oracle-analyzer 已自带 SKILL.md（已完善的 Hermes Skill 格式）
2. 用户在 Hermes Web UI 中通过聊天调用：
   - `/skill buffett-oracle` 加载技能
   - 或 `hermes skills install <url>` 安装
3. 通过自然语言交互：`分析苹果AAPL，使用巴菲特人格`
4. 所有 Agent 分析在后台运行，结果流式返回

**优点**：无需改一行 hermes-web-ui 代码，利用现有 Agent Bridge

### 方案 B：独立 FastAPI Web + iframe 嵌入
**难度**: ⭐⭐（3天）
**工作量**: 中等
**用户心智负担**: 中

1. buffett-oracle-analyzer 已有 FastAPI dashboard（`dashboard/app.py`）
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
  └─ buffett-oracle-analyzer/SKILL.md 已完善
  
Phase 2: Skill 发布
  ├─ 发布到 Hermes Skills Hub
  └─ 用户：hermes skills install buffett-oracle

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

### buffett-oracle-analyzer API（FastAPI）

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

---

*最后更新: 2026-05-21*
