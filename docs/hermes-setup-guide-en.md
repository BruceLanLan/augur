English | [中文](hermes-setup-guide.md)

# Hermes Agent Integration with Augur - Complete Guide

## Prerequisites

1. Hermes Agent is installed on your VPS (`npm install -g hermes-agent` or Docker)
2. Hermes Web UI is running
3. Augur is installed (`pip install -e .`)

---

## Method 1: MCP Server Integration (Recommended, Zero-Intrusion)

This is the simplest method. Augur runs as an MCP Server that Hermes automatically discovers and calls.

### Step 1: Verify Augur MCP Server is Available

```bash
# Test on your VPS
augur mcp-server
# If no errors appear, it's working (ctrl+c to exit)
```

### Step 2: Configure Hermes MCP

Edit your Hermes configuration file (usually at `~/.hermes/config.yaml` or in the Hermes Web UI settings page):

```yaml
mcp_servers:
  augur-agents:
    command: augur
    args: [mcp-server]
    description: "18 legendary investor multi-agent consensus analysis system"
    env:
      AUGUR_CONFIG: "~/.augur/config.yaml"
```

### Step 3: Verify in Hermes Web UI

1. Open Hermes Web UI
2. Navigate to **Settings > MCP Servers**
3. You should see `augur-agents` registered
4. **7 tools** should be available:
   - `augur_analyze` - Single or all 18 investor analysis (with key_findings/risks)
   - `augur_consensus` - 18-master weighted consensus (with Kelly position sizing)
   - `augur_fetch` - Fetch live market data only (no analysis)
   - `augur_list_personas` - List all 18 investors
   - `augur_configure` - Configure LLM model per investor
   - `augur_create_persona` - Create custom YAML persona
   - `augur_debate` - Multi-round agent debate

> All analyze/consensus/debate tools support **auto yfinance data fetch**: if no metrics are passed, live data is fetched automatically.

### Step 4: Start a Conversation

In the Hermes chat interface, simply say:

```
Analyze Apple AAPL
```

Or be more specific:

```
Analyze NVDA using the Buffett framework, PE=45, gross margin 75%, ROE=85%
```

Hermes will automatically invoke the `augur_analyze` or `augur_consensus` tool.

---

## Method 2: Soul Injection (Profile Personalization)

Inject an investor's "soul" into each Hermes Profile, making the Profile itself embody a specific investment master.

### Step 1: View Available Personas

```bash
augur list-personas
```

### Step 2: Inject into Hermes Profile

```bash
# Create a "Buffett Profile"
augur inject-soul --profile buffett-advisor --persona buffett --format hermes --output-dir ~/.hermes/profiles/

# Create a "Duan Yongping Profile"
augur inject-soul --profile duan-advisor --persona duan_yongping --format hermes --output-dir ~/.hermes/profiles/

# Create a "Serenity Supply Chain Profile"
augur inject-soul --profile serenity-trader --persona serenity --format hermes --output-dir ~/.hermes/profiles/
```

### Step 3: Select Profile in Hermes Web UI

1. Switch Profile at the bottom of the sidebar
2. Select `buffett-advisor`
3. All conversations in this Profile will now respond from Buffett's perspective

---

## Method 3: Group Chat Mode

Add multiple Augur Agents as participants in Hermes Web UI's Group Chat.

### Step 1: Install Augur Skills

```bash
# Install all 18 masters
hermes skills install https://github.com/BruceLanLan/augur

# Or install individually
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/serenity
```

### Step 2: Create a Group Chat Room

1. Open **Group Chat** in Hermes Web UI
2. Create a new room: "Investment Committee"
3. Add participants:
   - @buffett (Value Investing)
   - @dalio (Macro)
   - @serenity (Supply Chain)
   - @duan_yongping (China Market)
   - Yourself

### Step 3: Use @mention in Group Chat

```
@buffett Analyze AAPL's current valuation
@serenity What are the bottlenecks in NVDA's supply chain?
@dalio How do you see the current macro environment?
```

Each Agent responds independently using their own persona and analytical framework.

---

## Method 4: Telegram Bot + Hermes Gateway

Connect Augur to Telegram through Hermes Platform Channels.

### Step 1: Configure Telegram Channel in Hermes Web UI

1. Go to the **Channels** page
2. Add the Telegram platform
3. Enter your Bot Token (obtained from @BotFather)

### Step 2: Bind Augur Skill

In the Channel settings, set the default Skill to `augur`.

### Step 3: Use in Telegram

```
/skill augur
Analyze AAPL
```

---

## Method 5: WeChat Integration (GeWeChat + Hermes)

### Step 1: Start GeWeChat Docker

```bash
docker compose --profile wechat up -d gewe
# Wait for ports 2531/2532 to be ready
```

### Step 2: Configure WeChat Channel in Hermes Web UI

1. Go to **Channels** page
2. Add WeChat platform
3. Configure GeWeChat API address: `http://localhost:2531`
4. Scan QR code to log in

### Step 3: Chat via WeChat

Send messages directly to the Bot:
```
Analyze AAPL
@Buffett Is Apple worth buying?
List investors
```

---

## Quick Verification Checklist

Run the following steps on your VPS:

```bash
# 1. Pull latest code
cd augur && git pull

# 2. Install
pip install -e ".[all]"

# 3. Verify CLI
augur list-personas              # Should show 18 personas
augur analyze AAPL --persona buffett --pe 32 --roe 0.55  # Should return analysis

# 4. Start Dashboard (in another terminal)
python3 -m dashboard.app --port 8000 --cors

# 5. Open in browser
# http://VPS-IP:8000           -> Homepage
# http://VPS-IP:8000/stocks    -> Enter AAPL, click "Auto Fetch" + "Analyze"
# http://VPS-IP:8000/personas  -> See all 18 masters

# 6. Start MCP Server (after Hermes is configured)
augur mcp-server

# 7. Chat in Hermes Web UI
# "Analyze SIVE using Serenity's framework"
```

---

## FAQ

**Q: Hermes can't find the tools after MCP configuration?**
A: Make sure the `augur` command is in your PATH. You can use an absolute path:
```yaml
mcp_servers:
  augur-agents:
    command: /root/augur/venv/bin/augur
    args: [mcp-server]
```

**Q: Dashboard startup error about jinja2/httpx?**
A: Run `pip install jinja2 httpx`

**Q: Want to run Dashboard and MCP Server simultaneously?**
A: Use two terminals, or use tmux:
```bash
tmux new -d -s dashboard 'python3 -m dashboard.app --port 8000 --cors'
tmux new -d -s mcp 'augur mcp-server'
```

**Q: How to make agents in Hermes group chat use different models?**
A: Edit `config/agents.yaml` or modify via the Dashboard settings page.
