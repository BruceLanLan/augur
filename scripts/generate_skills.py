#!/usr/bin/env python3
"""
Generate Hermes-compatible SKILL.md files for all 18 Augur investment personas.

Usage:
    python scripts/generate_skills.py
    python scripts/generate_skills.py --persona buffett   # single persona
    python scripts/generate_skills.py --dry-run           # preview, no write
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from augur.soul import generate_soul, _PERSONA_MD_MAP  # noqa: E402
from augur.registry import AgentRegistry  # noqa: E402

# Skill metadata per persona
SKILL_META = {
    "buffett":       {"skill": "augur-buffett",       "model": "claude-sonnet-4-6", "lang": "en", "school": "value",      "desc": "Warren Buffett AI — moat-focused value investing, US blue-chip/financial/consumer"},
    "graham":        {"skill": "augur-graham",        "model": "claude-sonnet-4-6", "lang": "en", "school": "deep-value", "desc": "Benjamin Graham AI — deep value / margin of safety, beaten-down stocks"},
    "munger":        {"skill": "augur-munger",        "model": "claude-sonnet-4-6", "lang": "en", "school": "value",      "desc": "Charlie Munger AI — lattice thinking, cross-discipline analysis"},
    "lynch":         {"skill": "augur-lynch",         "model": "claude-sonnet-4-6", "lang": "en", "school": "garp",       "desc": "Peter Lynch AI — GARP / PEG, consumer growth, everyday observations"},
    "dalio":         {"skill": "augur-dalio",         "model": "claude-sonnet-4-6", "lang": "en", "school": "macro",      "desc": "Ray Dalio AI — macro / all-weather portfolio, debt cycles"},
    "soros":         {"skill": "augur-soros",         "model": "claude-sonnet-4-6", "lang": "en", "school": "macro",      "desc": "George Soros AI — reflexivity / macro trading, crisis and momentum"},
    "marks":         {"skill": "augur-marks",         "model": "claude-sonnet-4-6", "lang": "en", "school": "cycle",      "desc": "Howard Marks AI — cycle / contrarian, second-level thinking"},
    "cathie_wood":   {"skill": "augur-cathie-wood",   "model": "claude-sonnet-4-6", "lang": "en", "school": "growth",     "desc": "Cathie Wood AI — disruptive innovation, AI/genomics/blockchain"},
    "fisher":        {"skill": "augur-fisher",        "model": "claude-sonnet-4-6", "lang": "en", "school": "growth",     "desc": "Philip Fisher AI — growth quality / scuttlebutt, tech and specialty"},
    "thiel":         {"skill": "augur-thiel",         "model": "claude-sonnet-4-6", "lang": "en", "school": "monopoly",   "desc": "Peter Thiel AI — 0→1 monopoly thinking, tech platforms and deep tech"},
    "arps":          {"skill": "augur-arps",          "model": "claude-sonnet-4-6", "lang": "en", "school": "macro",      "desc": "ARPS AI — real rates + crypto/gold macro, inflation hedging"},
    "aschenbrunner": {"skill": "augur-aschenbrenner", "model": "claude-opus-4-8",   "lang": "en", "school": "ai-geo",     "desc": "Leopold Aschenbrenner AI — AGI infrastructure + geopolitics, AI/semiconductor supply chains"},
    "aschenbrenner": {"skill": "augur-aschenbrenner", "model": "claude-opus-4-8",   "lang": "en", "school": "ai-geo",     "desc": "Leopold Aschenbrenner AI — AGI infrastructure + geopolitics, AI/semiconductor supply chains"},
    "dayu":          {"skill": "augur-dayu",          "model": "claude-sonnet-4-6", "lang": "en", "school": "momentum",   "desc": "大宇 (BTCdayu) AI — information edge / sentiment momentum, Crypto and meme"},
    "duan_yongping": {"skill": "augur-duan-yongping", "model": "claude-sonnet-4-6", "lang": "zh", "school": "benfun",     "desc": "段永平 AI — 本分·极度集中，消费电子与平台"},
    "zhang_lei":     {"skill": "augur-zhang-lei",     "model": "claude-sonnet-4-6", "lang": "zh", "school": "structural", "desc": "张磊（高瓴）AI — 结构性长期价值，消费升级与医疗"},
    "li_lu":         {"skill": "augur-li-lu",         "model": "claude-sonnet-4-6", "lang": "zh", "school": "deep-value", "desc": "李录（喜马拉雅）AI — 深度价值/安全边际，港股A股低估蓝筹"},
    "dan_bin":       {"skill": "augur-dan-bin",       "model": "claude-sonnet-4-6", "lang": "zh", "school": "brand",      "desc": "但斌（东方港湾）AI — 品牌护城河·时代Beta，中国消费龙头"},
    "serenity":      {"skill": "augur-serenity",      "model": "claude-sonnet-4-6", "lang": "en", "school": "ai-supply",  "desc": "Serenity AI — AI/semiconductor supply chain bottlenecks, chokepoint assets"},
}

ZH_TOOL_SECTION = """
## 可用工具（Augur MCP）

启动 `augur-mcp` 后，以下工具自动可用：

- `mcp_augur_fetch` — 获取实时股价与财务数据（yfinance）
- `mcp_augur_analyze` — 运行全量18位大师评分
- `mcp_augur_consensus` — 获取加权共识信号 + Kelly 仓位建议
- `mcp_augur_debate` — 与其他大师辩论
- `mcp_augur_committee` — 召开投资委员会

## 配置 MCP

```yaml
# Hermes config.yaml
mcp_servers:
  augur:
    command: augur-mcp
```

```json
// Claude Desktop claude_desktop_config.json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

## 使用示例

```
/skill {skill_name}
"分析 AAPL，市值 3.3T，PE=32，ROE=55%，科技板块"

"腾讯港股 00700，你怎么看现在的估值？"
```
"""

EN_TOOL_SECTION = """
## Available Tools (Augur MCP)

Start `augur-mcp` to enable these tools automatically:

- `mcp_augur_fetch` — Real-time price and financials (yfinance)
- `mcp_augur_analyze` — Run all 18-master consensus scoring
- `mcp_augur_consensus` — Weighted consensus signal + Kelly position
- `mcp_augur_debate` — Structured debate with other masters
- `mcp_augur_committee` — Convene an investment committee

## MCP Setup

```yaml
# Hermes config.yaml
mcp_servers:
  augur:
    command: augur-mcp
```

```json
// Claude Desktop claude_desktop_config.json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

## Example Usage

```
/skill {skill_name}
"Analyze AAPL — market cap $3.3T, PE=32, ROE=55%, Technology sector"

"Should I add to my NVDA position at current levels?"
```
"""


def skill_template(persona_id: str, meta: dict, soul: str) -> str:
    skill_name = meta["skill"]
    lang = meta["lang"]
    raw_section = ZH_TOOL_SECTION if lang == "zh" else EN_TOOL_SECTION
    tool_section = raw_section.replace("{skill_name}", skill_name)

    return f"""---
name: {skill_name}
description: "{meta['desc']}"
version: 9.0.0
author: BruceBlue (https://x.com/BruceBlue)
license: MIT
platforms: [linux, macos, windows]
model:
  default: {meta['model']}
  alternatives: [claude-sonnet-4-6, gpt-4o, deepseek-chat]
metadata:
  augur:
    persona: {persona_id}
    school: {meta['school']}
    language: {lang}
    mcp_required: augur-mcp
compatibility: "Hermes Studio, Claude Desktop, any MCP-compatible client"
---

{soul}

{tool_section}
"""


def committee_skill() -> str:
    return """---
name: augur-committee
description: "Augur Investment Committee — Convene 2-18 masters for structured multi-agent analysis and verdict"
version: 9.0.0
author: BruceBlue (https://x.com/BruceBlue)
license: MIT
platforms: [linux, macos, windows]
model:
  default: claude-sonnet-4-6
metadata:
  augur:
    type: committee-coordinator
    mcp_required: augur-mcp
compatibility: "Hermes Studio, Claude Desktop, any MCP-compatible client"
---

# Augur Investment Committee — 投资委员会

You are the **Augur Committee Chair** — a neutral facilitator who convenes investment masters, organizes structured debate, and synthesizes verdicts.

You are NOT one of the 18 masters yourself. Your role is:
1. **Recruit** the right masters for the question at hand
2. **Facilitate** — each master analyzes independently, no groupthink
3. **Surface dissent** — minority views are as important as consensus
4. **Synthesize** — weighted verdict with Kelly position sizing

## Committee Agenda

For each session:
1. **Opening** — state the ticker, question, and which masters are attending
2. **Independent opinions** — each master speaks without seeing others' views first
3. **Cross-examination** — masters may challenge each other's assumptions
4. **Dissent recording** — document any strong disagreements
5. **Verdict** — weighted consensus signal + confidence + Kelly position

## Available Tools (Augur MCP)

- `mcp_augur_committee` — Run the full committee session (returns structured opinions + verdict)
- `mcp_augur_analyze` — Individual master scoring
- `mcp_augur_fetch` — Real-time market data
- `mcp_augur_consensus` — Weighted consensus calculation

## Example Usage

```
/skill augur-committee
"NVDA 委员会 — 巴菲特、段永平、Cathie Wood 和 Aschenbrenner，当前 PE=35，AI 芯片供应商"

"Convene full committee on TSLA — all 18 masters, focus on whether the EV moat is real"
```

## MCP Setup

```yaml
# Hermes config.yaml
mcp_servers:
  augur:
    command: augur-mcp
```
"""


def generate_all(only_persona=None, dry_run: bool = False) -> None:
    registry = AgentRegistry()
    skills_dir = ROOT / "skills"

    targets = list(SKILL_META.items())
    if only_persona:
        targets = [(pid, m) for pid, m in targets if pid == only_persona]
        if not targets:
            print(f"ERROR: persona '{only_persona}' not found in SKILL_META")
            sys.exit(1)

    generated = 0
    for persona_id, meta in targets:
        agent = registry.get(persona_id)
        if not agent:
            print(f"  SKIP {persona_id} — not in registry")
            continue

        try:
            soul = generate_soul(persona_id)
        except Exception as e:
            print(f"  ERROR {persona_id}: {e}")
            continue

        content = skill_template(persona_id, meta, soul)
        skill_dir = skills_dir / meta["skill"]

        if dry_run:
            print(f"  DRY-RUN {meta['skill']}/ — {len(content)} chars")
        else:
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
            print(f"  ✓ {meta['skill']}/SKILL.md — {len(content)} chars")

        generated += 1

    # Committee skill
    if not only_persona:
        committee_content = committee_skill()
        committee_dir = skills_dir / "augur-committee"
        if dry_run:
            print(f"  DRY-RUN augur-committee/ — {len(committee_content)} chars")
        else:
            committee_dir.mkdir(parents=True, exist_ok=True)
            (committee_dir / "SKILL.md").write_text(committee_content, encoding="utf-8")
            print(f"  ✓ augur-committee/SKILL.md — {len(committee_content)} chars")

    print(f"\nDone: {generated} persona skills + committee skill")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Augur agent SKILL.md files")
    parser.add_argument("--persona", help="Generate only this persona (e.g. buffett)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    generate_all(only_persona=args.persona, dry_run=args.dry_run)
