/* ============================================================
   Augur UI Kit — shared mock data
   The Council of Masters + market mock data.
   Exposed on window for the babel-scoped components.
   ============================================================ */

const SCHOOLS = {
  value:    { label: 'Classic Value', zh: '经典价值', glyph: '⚔', color: 'var(--amber)' },
  growth:   { label: 'Growth · Disruption', zh: '成长创新', glyph: '🚀', color: 'var(--crystal)' },
  macro:    { label: 'Macro · Cycle', zh: '宏观周期', glyph: '🌐', color: '#a78bfa' },
  china:    { label: 'China Masters', zh: '中国投资人', glyph: '🇨🇳', color: 'var(--gilt)' },
};

// 14 of the 18-master council (those with portrait art).
const MASTERS = [
  { id:'buffett',        name:'Warren Buffett',  zh:'巴菲特',   school:'value',  framework:'Moat · predictable earnings · FCF',     best:'Consumer / financial blue-chips',   score:8.4, sig:'buy'  },
  { id:'munger',         name:'Charlie Munger',  zh:'芒格',     school:'value',  framework:'Latticework of mental models · invert', best:'Misunderstood quality businesses',  score:7.8, sig:'buy'  },
  { id:'graham',         name:'Ben Graham',      zh:'格雷厄姆', school:'value',  framework:'Margin of safety · PE<15 PB<1.5',      best:'Deep-value, cigar-butt names',      score:4.9, sig:'neutral' },
  { id:'fisher',         name:'Philip Fisher',   zh:'费雪',     school:'value',  framework:'Scuttlebutt · durable gross margin',    best:'High-quality compounders',          score:7.6, sig:'buy'  },
  { id:'li_lu',          name:'Li Lu',           zh:'李录',     school:'value',  framework:'Deep value · wide margin of safety',    best:'Undervalued HK / A-shares',         score:6.2, sig:'neutral' },
  { id:'lynch',          name:'Peter Lynch',     zh:'彼得林奇', school:'growth', framework:'PEG < 1.5 · invest in what you know',   best:'GARP growth stories',               score:7.1, sig:'buy'  },
  { id:'cathie_wood',    name:'Cathie Wood',     zh:'凯西伍德', school:'growth', framework:"Wright's Law · TAM expansion",          best:'AI / genomics / blockchain',        score:7.9, sig:'buy'  },
  { id:'thiel',          name:'Peter Thiel',     zh:'彼得蒂尔', school:'growth', framework:'0→1 monopoly · contrarian truth',       best:'Platform / deep tech',              score:6.8, sig:'neutral' },
  { id:'dalio',          name:'Ray Dalio',       zh:'达利欧',   school:'macro',  framework:'All-weather · debt cycles',             best:'Macro rotation',                    score:5.1, sig:'neutral' },
  { id:'soros',          name:'George Soros',    zh:'索罗斯',   school:'macro',  framework:'Reflexivity · self-reinforcing trend',  best:'Trend trades',                      score:5.6, sig:'neutral' },
  { id:'marks',          name:'Howard Marks',    zh:'霍华德马克斯', school:'macro', framework:'Pendulum of mood · 2nd-order thinking', best:'Cycle bottoms',                  score:3.8, sig:'sell' },
  { id:'duan_yongping',  name:'Duan Yongping',   zh:'段永平',   school:'china',  framework:'本分 (honesty) · extreme focus',        best:'Clear-model consumer tech',         score:8.1, sig:'buy'  },
  { id:'zhang_lei',      name:'Zhang Lei',       zh:'张磊',     school:'china',  framework:'Structural long-term value',            best:'China growth tracks',               score:7.4, sig:'buy'  },
  { id:'dayu',           name:'Dayu',            zh:'大宇',     school:'china',  framework:'Information edge · sentiment momentum',  best:'Crypto / digital assets',           score:6.6, sig:'neutral' },
];

const MARKET = [
  { sym:'NVDA',  name:'NVIDIA',        px:135.20,  ch:+2.41 },
  { sym:'AAPL',  name:'Apple',         px:226.80,  ch:+0.62 },
  { sym:'TSLA',  name:'Tesla',         px:241.05,  ch:-1.12 },
  { sym:'MSFT',  name:'Microsoft',     px:418.30,  ch:+0.34 },
  { sym:'SPX',   name:'S&P 500',       px:5430.12, ch:+0.18 },
  { sym:'BTC',   name:'Bitcoin',       px:67240,   ch:+3.05 },
  { sym:'GOLD',  name:'Gold',          px:2358.4,  ch:+0.71 },
  { sym:'700',   name:'Tencent',       px:382.60,  ch:-0.44 },
];

const TAPE = [
  ['SPX','5,430.12','+0.18%','up'],['NDX','19,210.4','+0.41%','up'],['DJI','38,904','-0.12%','down'],
  ['VIX','13.20','-2.4%','down'],['BTC','67,240','+3.05%','up'],['ETH','3,512','+1.8%','up'],
  ['GOLD','2,358','+0.71%','up'],['WTI','78.40','-0.9%','down'],['US10Y','4.28%','+0.02','up'],
];

// A pre-baked consensus for the demo analysis (NVDA)
const CONSENSUS = {
  ticker:'NVDA', name:'NVIDIA Corp', price:135.20, pe:45.0, roe:0.65, gm:0.78,
  signal:'BULLISH', score:7.6, confidence:82, kelly:9.2,
  bull:[
    'CUDA software moat + datacenter TAM still compounding',
    'Gross margin 78% — pricing power intact through the cycle',
    'Blackwell ramp front-loads FY revenue visibility',
  ],
  bear:[
    'Valuation rich at 45× — little margin for a demand air-pocket',
    'Customer concentration: a few hyperscalers drive most growth',
    'Cyclical semi history warns against extrapolating peak demand',
  ],
};

Object.assign(window, { SCHOOLS, MASTERS, MARKET, TAPE, CONSENSUS });
