# Augur — Dashboard UI Kit

A high-fidelity recreation of the **Augur** terminal: a multi-agent investment
analysis dashboard where 18 legendary investors analyse a ticker in parallel and
return a single Kelly-sized consensus signal.

**The fusion:** Bloomberg trading-terminal (dark, amber, data-dense) × Dragon
Quest / Octopath **HD-2D** (pixel owl oracle, parchment scrolls, JRPG dialogue,
gilt medallions). Numbers stay in the terminal register; brand & narrative
moments use the oracle register.

## Run it
Open `index.html`. It loads React 18 + Babel and the JSX components below.
Foundations come from `../../colors_and_type.css` + `../../augur.css`; screen
layout from `kit.css`. Portraits resolve from `../../assets/avatars/`.

## Screens (interactive click-thru)
| Screen | File | What it shows |
|---|---|---|
| **Dashboard** | `Dashboard.jsx` | Ticker tape · owl hero + ticker input · global market board · recent prophecies · featured masters |
| **Stock Analysis** | `StockAnalysis.jsx` | "Summon the council" loading → score ring · BULLISH verdict · 18-master scorecard · bull/bear debate · oracle dialogue · parchment deep-report |
| **The Council** | `Council.jsx` | Gilt-medallion master roster · school filters · click a master → detail dialogue overlay |

## Flow
- Type a ticker (or click a chip) on the Dashboard → animated "council summoning"
  loading → full consensus report.
- Sidebar switches screens. Click any master medallion for their detail card.

## Components
- `Sidebar.jsx` — Bloomberg nav rail with the owl crest + the product's real nav icons.
- `data.jsx` — mock data: the 14-portrait council (`MASTERS`), `MARKET`, `TAPE`, a baked `CONSENSUS`.

## Notes / fidelity
- Visuals are lifted from the real dashboard CSS (`dashboard/static/css/bloomberg.css`)
  and template structure (`dashboard/templates/`) in `BruceLanLan/augur`.
- This is a **cosmetic recreation** — no live data, no backend. The HD-2D layer
  (medallions, dialogue, parchment, pixel type) is the brand direction added on top.
- Master **portraits** are the pixel busts shipped in the repo. To improve a
  likeness, drop a corrected bust into `assets/avatars/<id>.png` (same filename) —
  it flows into every medallion automatically.
