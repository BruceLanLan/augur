[English](hermes-setup-guide-en.md) | 中文

# Hermes Agent 接入 Augur - 完整指引

## 前置条件

1. VPS 上已安装 Hermes Agent (`npm install -g hermes-agent` 或 Docker)
2. Hermes Web UI 已运行
3. Augur 已安装 (`pip install -e .`)

---

## 方式一：MCP Server 接入（推荐，零侵入）

这是最简单的方式。Augur 作为 MCP Server 被 Hermes 自动发现和调用。

### Step 1: 确认 Augur MCP Server 可用

```bash
# 在 VPS 上测试
augur mcp-server
# 如果没有报错就说明正常（ctrl+c 退出）
```

### Step 2: 配置 Hermes 的 MCP

编辑 Hermes 配置文件（通常在 `~/.hermes/config.yaml` 或 Hermes Web UI 的设置页面）：

```yaml
mcp_servers:
  augur-agents:
    command: augur
    args: [mcp-server]
    description: "18位投资大师多Agent共识分析系统"
    env:
      AUGUR_CONFIG: "~/.augur/config.yaml"
```

### Step 3: 在 Hermes Web UI 中验证

1. 打开 Hermes Web UI
2. 进入 **Settings > MCP Servers**
3. 应该能看到 `augur-agents` 已注册
4. **7 个工具**应该可用：
   - `augur_analyze` - 单投资人或全部 18 位分析（含 key_findings/risks）
   - `augur_consensus` - 18 位加权共识（含 Kelly 仓位建议）
   - `augur_fetch` - 仅获取实时数据（不分析）
   - `augur_list_personas` - 列出全部 18 位投资人
   - `augur_configure` - 配置每位投资人使用的 LLM 模型
   - `augur_create_persona` - 创建自定义 YAML 投资人
   - `augur_debate` - 多 Agent 多轮辩论

> 所有 analyze/consensus/debate 工具都支持**自动 yfinance 数据获取**：不传指标时自动抓取实时数据。

### Step 4: 开始对话

在 Hermes 聊天界面中直接说：

```
分析一下苹果 AAPL
```

或者更具体：

```
用巴菲特框架分析 NVDA，PE=45，毛利率75%，ROE=85%
```

Hermes 会自动调用 `augur_analyze` 或 `augur_consensus` 工具。

---

## 方式二：Soul 注入（Profile 人格化）

给 Hermes 的每个 Profile 注入投资人"灵魂"，让 Profile 本身就是某位投资大师。

### Step 1: 查看可用人格

```bash
augur list-personas
```

### Step 2: 注入到 Hermes Profile

```bash
# 创建一个"巴菲特 Profile"
augur inject-soul --profile buffett-advisor --persona buffett --format hermes --output-dir ~/.hermes/profiles/

# 创建一个"段永平 Profile"
augur inject-soul --profile duan-advisor --persona duan_yongping --format hermes --output-dir ~/.hermes/profiles/

# 创建一个"Serenity 供应链 Profile"
augur inject-soul --profile serenity-trader --persona serenity --format hermes --output-dir ~/.hermes/profiles/
```

### Step 3: 在 Hermes Web UI 中选择 Profile

1. 在侧边栏底部切换 Profile
2. 选择 `buffett-advisor`
3. 现在这个 Profile 的所有对话都会以巴菲特的视角回答

---

## 方式三：Group Chat 群聊模式

在 Hermes Web UI 的 Group Chat 中添加多个 Augur Agent 作为参与者。

### Step 1: 安装 Augur Skills

```bash
# 安装全部 18 位大师
hermes skills install https://github.com/BruceLanLan/augur

# 或安装单个
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/serenity
```

### Step 2: 创建群聊房间

1. 在 Hermes Web UI 中打开 **Group Chat**
2. 创建新房间："投资委员会"
3. 添加参与者：
   - @buffett (价值投资)
   - @dalio (宏观)
   - @serenity (供应链)
   - @duan_yongping (中国市场)
   - 你自己

### Step 3: 在群聊中 @mention

```
@buffett 分析 AAPL 当前估值
@serenity NVDA 供应链有什么瓶颈？
@dalio 当前宏观环境怎么看？
```

每个 Agent 会用自己的人格和框架独立回答。

---

## 方式四：Telegram Bot + Hermes Gateway

通过 Hermes 的 Platform Channels 将 Augur 接入 Telegram。

### Step 1: 在 Hermes Web UI 配置 Telegram 通道

1. 进入 **Channels** 页面
2. 添加 Telegram 平台
3. 输入 Bot Token（从 @BotFather 获取）

### Step 2: 绑定 Augur Skill

在 Channel 设置中，指定默认 Skill 为 `augur`。

### Step 3: 在 Telegram 中使用

```
/skill augur
分析 AAPL
```

---

## 方式五：微信接入（GeWeChat + Hermes）

### Step 1: 启动 GeWeChat Docker

```bash
docker compose --profile wechat up -d gewe
# 等待 2531/2532 端口就绪
```

### Step 2: 在 Hermes Web UI 配置微信通道

1. **Channels** 页面
2. 添加 WeChat 平台
3. 配置 GeWeChat API 地址：`http://localhost:2531`
4. 扫码登录

### Step 3: 在微信中对话

直接发消息给 Bot：
```
分析 AAPL
@巴菲特 苹果值得买吗
投资人列表
```

---

## 快速验证清单

在你的 VPS 上依次执行：

```bash
# 1. 拉最新代码
cd augur && git pull

# 2. 安装
pip install -e ".[all]"

# 3. 验证 CLI
augur list-personas              # 应该显示 18 位
augur analyze AAPL --persona buffett --pe 32 --roe 0.55  # 应该返回分析结果

# 4. 启动 Dashboard (另一个终端)
python3 -m dashboard.app --port 8000 --cors

# 5. 浏览器访问
# http://VPS-IP:8000           → 首页
# http://VPS-IP:8000/stocks    → 输入 AAPL，点击"自动获取"+"分析"
# http://VPS-IP:8000/personas  → 看到 18 位大师

# 6. 启动 MCP Server（Hermes 配置好后）
augur mcp-server

# 7. 在 Hermes Web UI 对话
# "用 Serenity 的框架分析一下 SIVE"
```

---

## 常见问题

**Q: MCP 配置后 Hermes 找不到工具？**
A: 确认 `augur` 命令在 PATH 里。可以用绝对路径：
```yaml
mcp_servers:
  augur-agents:
    command: /root/augur/venv/bin/augur
    args: [mcp-server]
```

**Q: Dashboard 启动报错 jinja2/httpx？**
A: 运行 `pip install jinja2 httpx`

**Q: 想同时跑 Dashboard 和 MCP Server？**
A: 用两个终端，或用 tmux：
```bash
tmux new -d -s dashboard 'python3 -m dashboard.app --port 8000 --cors'
tmux new -d -s mcp 'augur mcp-server'
```

**Q: 如何让 Hermes 群聊里的 Agent 用不同模型？**
A: 编辑 `config/agents.yaml` 或通过 Dashboard 设置页修改。
