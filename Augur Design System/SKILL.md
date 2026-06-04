---
name: augur-design
description: Use this skill to generate well-branded interfaces and assets for Augur — the multi-agent AI investment oracle (Bloomberg trading-terminal × Dragon Quest HD-2D pixel aesthetic) — for production or throwaway prototypes/mocks. Contains brand guidelines, color & type tokens, fonts, the owl + master pixel assets, and an interactive dashboard UI kit.
user-invocable: true
---

# Augur Design Skill

Augur is an AI investment decision council: 18 legendary investors analyse a ticker
in parallel into one Kelly-sized consensus signal. The brand fuses a **Bloomberg
trading terminal** (dark, amber, data-dense, mono numbers) with **Dragon Quest /
Octopath HD-2D** lore (pixel owl oracle, gilt master medallions, parchment scrolls,
JRPG dialogue boxes). The governing rule: **Terminal for numbers, Oracle for narrative.**

## Start here
1. Read `README.md` — brand idea, Content Fundamentals, Visual Foundations, Iconography.
2. Load the tokens: `colors_and_type.css` (colors, type scale, light theme) then
   `augur.css` (components). Import both; build with the semantic vars/classes.
3. Skim `preview/` for how each token/component should look, and
   `ui_kits/dashboard/` (+ its README) for real screen compositions and the nav icon SVGs.

## Working with assets
- Brand sprites live in `assets/` — owl logos, `favicon.png`, `hd2d-oracle-hall.png`
  (the north-star brand image), and `assets/avatars/` (14 master pixel busts).
- **Copy assets out** into your design's folder and reference them with relative
  paths — don't hotlink across projects. Keep sprites crisp (`image-rendering: pixelated`).
- Fonts load from Google Fonts: Inter, JetBrains Mono, Press Start 2P, Silkscreen.

## How to build
- **Visual artifacts** (slides, mocks, throwaway prototypes): copy the assets and
  CSS you need and produce self-contained static HTML for the user to view.
- **Production code**: copy assets and lift the exact tokens/rules from
  `colors_and_type.css` + `augur.css`; mirror the real product structure in
  `BruceLanLan/augur` (`dashboard/static/css/bloomberg.css`, `dashboard/templates/`).
- Numbers → JetBrains Mono, amber, terminal cards. Brand/story → pixel type, gilt,
  parchment, dialogue, medallions. Don't put pixel kitsch behind live data.

## If invoked with no brief
Ask what they want to build (a screen, a deck, a marketing page, a component), ask
a few clarifying questions (surface, audience, light/dark, how much HD-2D vs.
straight terminal), then act as an expert Augur designer — output HTML artifacts or
production code as needed. Keep the disclaimer present: *for research only, not
investment advice.*
