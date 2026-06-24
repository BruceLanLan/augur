#!/usr/bin/env python3
"""
Generate Hermes-compatible SKILL.md files for all 18 Augur investment personas.
Also generates OpenClaw/universal manifest.json for each skill directory.

Usage:
    python scripts/generate_skills.py
    python scripts/generate_skills.py --persona buffett   # single persona
    python scripts/generate_skills.py --dry-run           # preview, no write
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from augur import __version__ as AUGUR_VERSION  # noqa: E402
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

# School-based tags for manifest.json
SCHOOL_TAGS = {
    "value":      ["investing", "value", "moat", "fundamental"],
    "deep-value": ["investing", "deep-value", "margin-of-safety", "contrarian"],
    "garp":       ["investing", "garp", "growth", "peg"],
    "macro":      ["investing", "macro", "global", "cycles"],
    "cycle":      ["investing", "cycle", "contrarian", "risk"],
    "growth":     ["investing", "growth", "innovation", "disruptive"],
    "monopoly":   ["investing", "monopoly", "zero-to-one", "tech"],
    "ai-geo":     ["investing", "ai", "geopolitics", "semiconductor"],
    "ai-supply":  ["investing", "ai", "semiconductor", "supply-chain"],
    "momentum":   ["investing", "momentum", "sentiment", "crypto"],
    "benfun":     ["investing", "benfun", "concentration", "consumer-electronics"],
    "structural": ["investing", "structural", "long-term", "consumer-upgrade"],
    "brand":      ["investing", "brand", "moat", "china-consumer"],
}


def generate_manifest(persona_id: str, meta: dict) -> dict:
    """Build a manifest.json dict for a persona skill."""
    skill_name = meta["skill"]
    tags = SCHOOL_TAGS.get(meta["school"], ["investing"])
    # Insert persona-keyed tag (e.g. "warren-buffett") as second element
    persona_tag = skill_name.replace("augur-", "")
    if persona_tag not in tags:
        tags = [tags[0], persona_tag] + tags[1:]

    return {
        "name": skill_name,
        "version": AUGUR_VERSION,
        "description": meta["desc"],
        "author": "BruceBlue (https://x.com/BruceBlue)",
        "license": "MIT",
        "type": "mcp-skill",
        "model": {
            "default": meta["model"],
            "alternatives": ["gpt-4o", "deepseek-chat"],
        },
        "mcp": {
            "server": "augur",
            "command": "augur-mcp",
            "required_tools": [
                "mcp_augur_analyze",
                "mcp_augur_fetch",
                "mcp_augur_consensus",
            ],
        },
        "compatibility": ["hermes", "openclaw", "claude-desktop", "any-mcp"],
        "tags": tags,
        "language": meta["lang"],
        "persona_id": persona_id,
    }


def generate_committee_manifest() -> dict:
    """Build a manifest.json dict for the committee coordinator skill."""
    return {
        "name": "augur-committee",
        "version": AUGUR_VERSION,
        "description": "Augur Investment Committee — Convene 2-18 masters for structured multi-agent analysis and verdict",
        "author": "BruceBlue (https://x.com/BruceBlue)",
        "license": "MIT",
        "type": "mcp-skill",
        "model": {
            "default": "claude-sonnet-4-6",
            "alternatives": ["gpt-4o", "deepseek-chat"],
        },
        "mcp": {
            "server": "augur",
            "command": "augur-mcp",
            "required_tools": [
                "mcp_augur_analyze",
                "mcp_augur_fetch",
                "mcp_augur_consensus",
                "mcp_augur_committee",
            ],
        },
        "compatibility": ["hermes", "openclaw", "claude-desktop", "any-mcp"],
        "tags": ["investing", "committee", "multi-agent", "consensus"],
        "language": "en",
        "type": "committee-coordinator",
    }


ZH_TOOL_SECTION = """
## 可用工具（Augur MCP，共13个）

启动 `augur-mcp` 后，以下工具自动可用：

- `mcp_augur_fetch` — 获取实时股价与财务数据（yfinance）
- `mcp_augur_analyze` — 运行全量18位大师评分
- `mcp_augur_consensus` — 获取加权共识信号 + Kelly 仓位建议
- `mcp_augur_debate` — 与其他大师辩论
- `mcp_augur_committee` — 召开投资委员会
- `mcp_augur_sentiment` — 获取社交情绪信号（StockTwits + 新闻）
- `mcp_augur_list_personas` — 列出全部18位大师
- `mcp_augur_configure` — 设置单个大师的模型参数
- `mcp_augur_create_persona` — 创建自定义 YAML 人格
- `mcp_augur_workflow` — 多步骤流水线：fetch→analyze→consensus→committee→debate→sentiment
- `mcp_augur_workspace_get` — 读取你的终端布局 / 启用大师 / 委员会预设
- `mcp_augur_workspace_set` — 代你修改终端配置
- `mcp_augur_workspace_profiles` — 列出/创建/切换/删除终端配置

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
## Available Tools (Augur MCP, 13 total)

Start `augur-mcp` to enable these tools automatically:

- `mcp_augur_fetch` — Real-time price and financials (yfinance)
- `mcp_augur_analyze` — Run all 18-master consensus scoring
- `mcp_augur_consensus` — Weighted consensus signal + Kelly position
- `mcp_augur_debate` — Structured debate with other masters
- `mcp_augur_committee` — Convene an investment committee
- `mcp_augur_sentiment` — Social sentiment signal (StockTwits + news)
- `mcp_augur_list_personas` — List all 18 masters
- `mcp_augur_configure` — Set per-master model parameters
- `mcp_augur_create_persona` — Create a custom YAML persona
- `mcp_augur_workflow` — Multi-step pipeline: fetch→analyze→consensus→committee→debate→sentiment
- `mcp_augur_workspace_get` — Read your terminal layout / enabled masters / committee preset
- `mcp_augur_workspace_set` — Modify your terminal config on your behalf
- `mcp_augur_workspace_profiles` — List/create/switch/delete terminal profiles

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
version: {AUGUR_VERSION}
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
    return f"""---
name: augur-committee
description: "Augur Investment Committee — Convene 2-18 masters for structured multi-agent analysis and verdict"
version: {AUGUR_VERSION}
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

## Available Tools (Augur MCP, 13 total)

- `mcp_augur_committee` — Run the full committee session (returns structured opinions + verdict)
- `mcp_augur_analyze` — Individual master scoring
- `mcp_augur_fetch` — Real-time market data
- `mcp_augur_consensus` — Weighted consensus calculation
- `mcp_augur_debate` — Structured debate with other masters
- `mcp_augur_sentiment` — Social sentiment signal (StockTwits + news)
- `mcp_augur_list_personas` — List all 18 masters
- `mcp_augur_configure` — Set per-master model parameters
- `mcp_augur_create_persona` — Create a custom YAML persona
- `mcp_augur_workflow` — Multi-step pipeline: fetch→analyze→consensus→committee→debate→sentiment
- `mcp_augur_workspace_get` — Read your terminal layout / enabled masters / committee preset
- `mcp_augur_workspace_set` — Modify your terminal config on your behalf
- `mcp_augur_workspace_profiles` — List/create/switch/delete terminal profiles

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

        manifest = generate_manifest(persona_id, meta)
        manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"

        if dry_run:
            print(f"  DRY-RUN {meta['skill']}/ — {len(content)} chars SKILL.md, {len(manifest_json)} chars manifest.json")
        else:
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
            (skill_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")
            print(f"  ✓ {meta['skill']}/SKILL.md + manifest.json — {len(content)} chars")

        generated += 1

    # Committee skill
    if not only_persona:
        committee_content = committee_skill()
        committee_dir = skills_dir / "augur-committee"
        committee_manifest = generate_committee_manifest()
        committee_manifest_json = json.dumps(committee_manifest, indent=2, ensure_ascii=False) + "\n"
        if dry_run:
            print(f"  DRY-RUN augur-committee/ — {len(committee_content)} chars SKILL.md, {len(committee_manifest_json)} chars manifest.json")
        else:
            committee_dir.mkdir(parents=True, exist_ok=True)
            (committee_dir / "SKILL.md").write_text(committee_content, encoding="utf-8")
            (committee_dir / "manifest.json").write_text(committee_manifest_json, encoding="utf-8")
            print(f"  ✓ augur-committee/SKILL.md + manifest.json — {len(committee_content)} chars")

    print(f"\nDone: {generated} persona skills + committee skill")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Augur agent SKILL.md files")
    parser.add_argument("--persona", help="Generate only this persona (e.g. buffett)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    generate_all(only_persona=args.persona, dry_run=args.dry_run)
