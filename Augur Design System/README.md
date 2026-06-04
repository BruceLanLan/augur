# 🦉 Augur — Design System

> **Augur** is your AI investment decision council. One ticker, **18 legendary
> investors** analysing in parallel, distilled into a single weighted, Kelly-sized
> consensus signal. *"Would Buffett buy this? How does Dalio read the macro risk?"*

This repository is the **brand & design system** for Augur — the foundations,
component library, and a high-fidelity UI kit for designing on-brand interfaces
and assets.

---

## The Brand Idea — Bloomberg × HD-2D

Augur fuses two worlds, and every design decision flows from holding both at once:

- **Bloomberg trading terminal** — the *data substrate*. Near-black surfaces,
  amber accent, JetBrains Mono everywhere a number lives, green/red signal tape,
  dense tables. Legibility first.
- **Dragon Quest / Octopath "HD-2D"** — the *oracle narrative*. Augur is a
  divining owl; the 18 masters are a **council of heroes**; analyses are
  **prophecies** delivered on parchment scrolls through JRPG dialogue boxes; each
  master is a **gilt medallion**. Pixel type for the wordmark, names and verdicts.

> **The rule that keeps it tasteful:** *Terminal for numbers, Oracle for narrative.*
> Pixel fonts, parchment and gold appear only on brand/story surfaces — never
> behind live market data.

The north-star image is `assets/hd2d-oracle-hall.png`: the pixel owl on a pedestal
in a cathedral of crystal-ball charts and parchment market scrolls, with a
dialogue box reading *"AUGUR — AI Investment Oracle."*

### Why a white owl?
In Japanese culture the white owl (フクロウ) is an omen of fortune & wisdom —
「不苦労」 ("no hardship") / 「福来郎」 ("fortune arrives"). The mark is always a
crisp pixel sprite, never blurred.

---

## Sources

This system was reverse-engineered from the real Augur product. If you have access,
explore these to build with higher fidelity:

- **GitHub — `BruceLanLan/augur`** · https://github.com/BruceLanLan/augur
  - `dashboard/static/css/bloomberg.css` — the live terminal CSS (color tokens, components)
  - `dashboard/templates/` — page structure (`base.html`, `index.html`, `stocks.html`, `personas.html`, `report_view.html`…)
  - `dashboard/static/images/` — the owl logo set & favicon
  - `docs/images/avatars/` — the 18 pixel-art master portraits
  - `docs/images/dq1-style-sample.png` — the HD-2D "oracle hall" brand reference
  - `README.md` / `README_EN.md` — product copy, the 18-master roster, feature list

The product also ships as an MCP server, Telegram/Slack/WeChat/Lark bots, and a CLI;
the dashboard (17 pages) is the surface this kit recreates.

---

## Content Fundamentals — how Augur writes

**Voice:** a calm, data-literate research desk *wearing the robe of an oracle.*
Two registers, deliberately mixed:

- **Terminal copy** is terse, quantitative, lowercase-leaning labels:
  `CONFIDENCE`, `KELLY SIZE`, `PE 45.0 · ROE 65%`, `BULLISH (13) · NEUTRAL (5)`.
  Numbers carry units; signals are ALL-CAPS (`BUY / SELL / HOLD`, `BULLISH`).
- **Oracle copy** is mythic but never silly — "council," "prophecy," "the owl
  speaks," "summon the masters," "heed the bears before you size." Used for
  headings, empty states, loading, and persona dialogue.

**Person:** addresses the user as *you* ("your AI investment council"), refers to
the system as *Augur / the Oracle*. Masters speak in first person ("My edge is…").

**Bilingual.** The product is zh-first with full EN i18n. Chinese names sit
alongside English (`巴菲特 · Buffett`). Keep both when space allows.

**Casing:** Inter headings are sentence case. Pixel labels / eyebrows / tags are
UPPERCASE. Tickers and signals are UPPERCASE mono.

**Emoji / glyphs:** used sparingly and *functionally* as faction crests
(⚔ Value · 🚀 Growth · 🌐 Macro · 🇨🇳 China) and the 🦉 mascot — not decoration.
Geometric marks (▸ ◈ ▲ ▼ ●) act as bullets, tape arrows and the JRPG ▼ chevron.

**Disclaimer, always:** *"仅供学习研究，不构成投资建议 / For research only, not investment advice."*

**Examples**
- Verdict: `BULLISH · 7.6/10 · confidence 82% · Kelly 9.2%`
- Oracle: *"The council has spoken. NVDA draws a BULLISH omen. Heed the bears before you size."*
- Empty: *"No prophecies yet — enter a ticker to summon the council."*

---

## Visual Foundations

**Color.** Near-black canvas ramp (`#0a0a0f` void → `#1e1e2e` elevated). One hero
accent: **amber `#ff8c00`** (links, focus, primary). Signals are the tape:
buy `#00c853`, sell `#ff1744`, neutral `#ffd600`, each with a ~12–15% tinted
background. A separate **oracle palette** — parchment `#e8dcc0`, gilt `#d4af37`,
oracle-purple `#3a2c6e`, crystal `#5cc8ff`, ink `#2a2118` — is reserved for lore
surfaces. A warm parchment-leaning **light theme** ships too. Imagery is warm and
golden (candle-lit HD-2D halls), and pixel sprites render crisp (`image-rendering: pixelated`).

**Type.** Four families, strict roles: **Inter** (UI chrome, prose) · **JetBrains
Mono** (every number/ticker, tabular) · **Press Start 2P** (wordmark + big
verdicts, *very* sparing) · **Silkscreen** (master names, eyebrows, tags,
dialogue). See `colors_and_type.css` for the full semantic scale.

**Spacing.** 4px base grid (`--space-1…8` = 4→64). Generous 16–24px gutters;
24/32px screen padding.

**Backgrounds.** Mostly flat near-black. Two textures used at very low opacity:
a 24px **pixel grid** (the HD-2D stone floor, on hero/sidebar) and faint amber
**CRT scanlines** for terminal panels. Hero/council panels add a soft radial
amber-or-gold glow from the top-left. No loud gradients on content.

**Borders & radii.** Terminal is sharp: 1px `#1e1e2e` borders, `--r-sm 4` /
`--r-md 8` / `--r-lg 12`. HD-2D frames are **hard-edged (0 radius)** with a 2px
gilt or ink border. Cards: subtle 1px border, no border by default → border
brightens + lifts on hover.

**Shadows / elevation.** Four steps: `shadow-card` (soft, hover), `shadow-pop`
(popovers/overlays), `shadow-glow` (amber focus ring), and the signature
**`shadow-pixel`** — a chunky `4px 4px 0` hard offset that makes JRPG buttons/boxes
"press in," plus **`shadow-gilt`** (gold bloom) for medallions & relic frames.

**Motion.** Mostly quick (150–250ms) `ease`/cubic-bezier fades and 1–3px hover
lifts. Brand moments use **stepped** easing (`steps()`) — the JRPG ▼ chevron bob,
the owl "summoning" bob, pixel-button press — so they feel sprite-animated, not
silky. Loading is a staged "council summoning" sequence. Respect
`prefers-reduced-motion`.

**Hover / press.** Hover: border → amber/gilt, slight `translateY(-2px)`,
background → `card-hover`. Press: `translateY(1px)`; pixel buttons translate into
their drop-shadow. Ghost/ticker chips invert to amber-on-fill.

**Transparency & blur.** Sparing. Tinted signal backgrounds (8–15%), the modal
overlay (`rgba(4,4,8,.78)` + 4px blur), amber washes for active nav. Never frosted
glass on data.

**Cards.** Default: `#14141f`, 1px border, 8px radius, 16px pad. **Master cards:**
gilt **medallion** (conic-gold cameo coin) + school-crest badge + parchment
nameplate + RPG stat line (score + conviction pips). **Scrolls** & **dialogue**
boxes are the oracle equivalents.

---

## Iconography

- **Line icons** — the product hand-rolls a small set of **stroke SVG** icons
  (1.5–2px, round caps, 24×24, `currentColor`) for navigation: dashboard grid,
  line-chart, bell, scanner, bookmark, wallet, clock, chat, people, gear, plus.
  These are recreated verbatim in `ui_kits/dashboard/Sidebar.jsx` — copy from
  there. No external icon font; no Font Awesome.
- **Faction crests** — emoji used *functionally* as school sigils
  (⚔ 🚀 🌐 🇨🇳) and the 🦉 mascot. Keep these; they're part of the system.
- **Geometric glyphs** — unicode marks do real work: `▸ ◈` (eyebrows/section
  ticks), `▲ ▼` (tape direction, vote arrows), `●` (conviction pips, status dot),
  `▼` (JRPG continue chevron).
- **Brand sprites** — the pixel owl (`assets/augur-owl-*.png`, `favicon.png`) and
  the 14 master pixel busts (`assets/avatars/`). Always crisp, never blurred.
- **Rule:** don't hand-draw new realistic SVG illustration. Use the owl, the
  medallion frame, the crests, and these glyphs. New master art should be pixel
  busts dropped into `assets/avatars/`.

If you need a broader UI icon (not in the nav set), match the existing **stroke
style** (Lucide/Feather-weight) rather than introducing a filled set.

---

## Index — what's in here

| File / folder | What it is |
|---|---|
| `README.md` | This document — brand, content, visual, iconography |
| `SKILL.md` | Agent Skill manifest (for Claude Code download) |
| `colors_and_type.css` | **Foundations** — all color + type tokens, semantic scale, light theme |
| `augur.css` | **Component library** — terminal + oracle components (cards, buttons, badges, dialogue, scroll, medallion, table, tape…) |
| `assets/` | Owl logos & favicon, `hd2d-oracle-hall.png` brand hero, `avatars/` (14 master pixel busts) |
| `preview/` | Design-system cards rendered in the Design System tab |
| `ui_kits/dashboard/` | **The UI kit** — interactive Bloomberg × HD-2D terminal recreation (see its own README) |

**UI kits**
- `ui_kits/dashboard/` — the Augur terminal: Dashboard · Stock Analysis · The Council.

*No slide template was provided, so no `slides/` are included.*

---

*MIT-licensed product by [BruceLanLan](https://github.com/BruceLanLan). This design
system is for building on-brand Augur interfaces. For research only — not
investment advice.*
