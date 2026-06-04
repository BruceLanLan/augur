/* Augur UI Kit — Dashboard (home) */
function Tape() {
  const items = window.TAPE;
  return (
    <div className="tape">
      <span style={{font:'700 0.6rem/1 var(--font-pixfin)',color:'var(--gilt)',letterSpacing:'1px',textTransform:'uppercase',flexShrink:0}}>◈ Tape</span>
      {items.map((t,i)=>(
        <span key={i} style={{flexShrink:0}}>
          <span className="sym">{t[0]}</span>
          <span style={{color:'var(--fg-1)'}}>{t[1]}</span>{' '}
          <span className={t[3]}>{t[2]}</span>
        </span>
      ))}
    </div>
  );
}

function Hero({ onAnalyze }) {
  const [val, setVal] = React.useState('');
  const submit = (t) => onAnalyze((t || val || 'NVDA').toUpperCase());
  return (
    <section className="hero gilt-edge">
      <div className="hero-glow"></div>
      <img src="../../assets/augur-owl-128.png" className="pixelated hero-owl" width="92" height="92" alt=""/>
      <div className="hero-eyebrow">▸ AI Investment Oracle</div>
      <h1 className="hero-title">Summon your council of <span>18 masters</span></h1>
      <p className="hero-sub">One ticker. Eighteen legendary investors analyse in parallel. One Kelly-sized consensus signal.</p>
      <div className="hero-input">
        <input className="field mono" placeholder="Enter ticker — NVDA, AAPL, TSLA…"
          value={val} onChange={e=>setVal(e.target.value)}
          onKeyDown={e=>{ if(e.key==='Enter') submit(); }} />
        <button className="pixel-btn dark" onClick={()=>submit()}>▶ Consult</button>
      </div>
      <div className="hero-chips">
        <span style={{font:'500 0.68rem/1 var(--font-mono)',color:'var(--fg-3)'}}>Try</span>
        {['NVDA','AAPL','TSLA','MSFT','BTC'].map(t=>(
          <span key={t} className="chip" onClick={()=>submit(t)}>{t}</span>
        ))}
      </div>
    </section>
  );
}

function MarketBoard() {
  return (
    <div className="aug-card">
      <div className="aug-card-head"><span>Global Market Board</span><span style={{color:'var(--fg-3)',font:'500 0.6rem/1 var(--font-mono)'}}>refresh 60s</span></div>
      <div className="mboard">
        {window.MARKET.map(m=>{
          const up = m.ch >= 0;
          return (
            <div key={m.sym} className={'mtile '+(up?'up':'down')}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline'}}>
                <div className="nm">{m.sym}</div>
                <div style={{font:'600 0.55rem/1 var(--font-pixfin)',color:'var(--fg-3)',textTransform:'uppercase',letterSpacing:'.5px'}}>{m.name}</div>
              </div>
              <div className="px">{m.px.toLocaleString()}</div>
              <div className="ch">{up?'▲ +':'▼ '}{m.ch}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RecentList({ onAnalyze }) {
  const recents = [
    ['NVDA','BULLISH','buy','7.6','2m ago'],
    ['AAPL','NEUTRAL','neutral','5.4','1h ago'],
    ['TSLA','BEARISH','sell','3.9','3h ago'],
    ['MSFT','BULLISH','buy','7.1','yesterday'],
  ];
  return (
    <div className="aug-card">
      <div className="aug-card-head"><span>Recent Prophecies</span></div>
      <ul className="recent">
        {recents.map((r,i)=>(
          <li key={i} onClick={()=>onAnalyze(r[0])}>
            <span className="rt">{r[0]}</span>
            <span className={'signal-badge '+r[2]} style={{fontSize:'0.62rem',padding:'2px 8px'}}>{r[1]}</span>
            <span style={{font:'600 0.82rem/1 var(--font-mono)',color:'var(--fg-2)',marginLeft:'auto'}}>{r[3]}</span>
            <span style={{font:'500 0.62rem/1 var(--font-mono)',color:'var(--fg-3)',width:'72px',textAlign:'right'}}>{r[4]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function FeaturedMasters({ go }) {
  const feat = window.MASTERS.slice(0,3);
  return (
    <div className="aug-card">
      <div className="aug-card-head"><span>Featured Masters</span><a onClick={go} style={{font:'600 0.62rem/1 var(--font-pixfin)',color:'var(--amber)',cursor:'pointer',textTransform:'uppercase'}}>View all ▸</a></div>
      <div style={{display:'flex',flexDirection:'column',gap:'2px'}}>
        {feat.map(m=>{
          const s = window.SCHOOLS[m.school];
          return (
            <div key={m.id} className="m-row" onClick={go}>
              <img src={'../../assets/avatars/'+m.id+'.png'} className="avatar" width="40" height="40" alt={m.name}/>
              <div style={{minWidth:0}}>
                <div style={{font:'var(--name)',color:'var(--fg-1)'}}>{m.name}</div>
                <div style={{font:'600 0.58rem/1.3 var(--font-pixfin)',color:s.color,textTransform:'uppercase'}}>{s.glyph} {s.label}</div>
              </div>
              <span style={{marginLeft:'auto',font:'700 1rem/1 var(--font-mono)',color:'var(--amber)'}}>{m.score}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Dashboard({ onAnalyze, go }) {
  return (
    <div>
      <Tape/>
      <div style={{padding:'24px 0 0'}}>
        <Hero onAnalyze={onAnalyze}/>
        <div style={{marginTop:'20px'}}><MarketBoard/></div>
        <div className="grid-2-1" style={{marginTop:'20px'}}>
          <RecentList onAnalyze={onAnalyze}/>
          <FeaturedMasters go={()=>go('council')}/>
        </div>
      </div>
    </div>
  );
}
window.Dashboard = Dashboard;
