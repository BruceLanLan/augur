/* Augur UI Kit — Stock Analysis (consensus result) */
function ScoreRing({ score }) {
  const pct = Math.round(score * 10);
  return (
    <div className="ring" style={{'--pct': pct}}>
      <div className="ring-in">
        <span className="ring-v">{score.toFixed(1)}</span>
        <span className="ring-l">/10</span>
      </div>
    </div>
  );
}

function ExecCard({ c }) {
  const sigClass = c.signal==='BULLISH'?'buy':c.signal==='BEARISH'?'sell':'neutral';
  return (
    <div className="exec gilt-edge">
      <div className="exec-glow"></div>
      <ScoreRing score={c.score}/>
      <div className="exec-mid">
        <div className="t-eyebrow" style={{color:'var(--gilt)'}}>◈ Council Consensus</div>
        <div className={'verdict '+sigClass} style={{margin:'6px 0 10px'}}>{c.signal}</div>
        <div className="exec-metrics">
          <div><span className="l">Confidence</span><span className="v">{c.confidence}%</span></div>
          <div><span className="l">Kelly Size</span><span className="v" style={{color:'var(--amber)'}}>{c.kelly}%</span></div>
          <div><span className="l">Price</span><span className="v">${c.price}</span></div>
          <div><span className="l">P/E</span><span className="v">{c.pe}</span></div>
        </div>
      </div>
      <div className="exec-votes">
        <div className="vote buy"><b>13</b><span>BULLISH</span></div>
        <div className="vote neutral"><b>1</b><span>NEUTRAL</span></div>
        <div className="vote sell"><b>0</b><span>BEARISH</span></div>
      </div>
    </div>
  );
}

function OracleSays({ c }) {
  return (
    <div className="dialogue" style={{marginTop:'16px'}}>
      <div className="speaker"><img src="../../assets/augur-owl-64.png" className="pixelated" width="20" height="20"/> The Oracle of Augur</div>
      <div>The council has spoken. <b style={{color:'var(--gilt-bright)'}}>{c.ticker}</b> draws a <b style={{color:'var(--signal-buy)'}}>{c.signal}</b> omen — score {c.score}, confidence {c.confidence}%. The Kelly oracle counsels a <b style={{color:'var(--gilt-bright)'}}>{c.kelly}%</b> position. Heed the bears before you size.</div>
      <span className="chevron">▼</span>
    </div>
  );
}

function ScorecardGrid() {
  return (
    <div style={{marginTop:'24px'}}>
      <div className="sec-title">18-Master Scorecard</div>
      <div className="sc-grid">
        {window.MASTERS.map(m=>{
          const cls = m.score>=6.5?'score-high':m.score>=4.5?'score-mid':'score-low';
          return (
            <div key={m.id} className="sc">
              <img src={'../../assets/avatars/'+m.id+'.png'} className="avatar" width="34" height="34" alt=""/>
              <div className="sc-nm">{m.zh}</div>
              <div className={'sc-score '+cls}>{m.score}</div>
              <span className={'signal-badge '+m.sig} style={{fontSize:'0.56rem',padding:'1px 7px'}}>{m.sig.toUpperCase()}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Debate({ c }) {
  return (
    <div style={{marginTop:'24px'}}>
      <div className="sec-title">Bull vs. Bear Debate</div>
      <div className="debate">
        <div className="d-panel bull">
          <div className="d-head" style={{color:'var(--signal-buy)'}}>▲ The Bull Case</div>
          <ul>{c.bull.map((b,i)=><li key={i}>{b}</li>)}</ul>
        </div>
        <div className="d-panel bear">
          <div className="d-head" style={{color:'var(--signal-sell)'}}>▼ The Bear Case</div>
          <ul>{c.bear.map((b,i)=><li key={i}>{b}</li>)}</ul>
        </div>
      </div>
    </div>
  );
}

function DeepReport({ c }) {
  return (
    <div style={{marginTop:'24px'}}>
      <div className="sec-title">Deep Prophecy · Generated Report</div>
      <div className="scroll" style={{marginTop:'14px'}}>
        <h4>◈ Augur Prophecy — {c.ticker}</h4>
        <p style={{margin:'0 0 8px'}}><b style={{color:'#6b4f1d'}}>Thesis.</b> {c.name} commands a durable software moat (CUDA) atop a structurally expanding datacenter TAM. Gross margin of {Math.round(c.gm*100)}% evidences pricing power that the council weights heavily.</p>
        <p style={{margin:'0 0 8px'}}><b style={{color:'#6b4f1d'}}>Tension.</b> At {c.pe}× earnings the name prices in flawless execution; the cycle-aware masters (Marks, Dalio) urge restraint.</p>
        <p style={{margin:0}}><span style={{color:'#8a6a2c'}}>▸ Verdict: accumulate on weakness, size with Kelly at {c.kelly}%. Re-rate risk is the dominant downside.</span></p>
      </div>
    </div>
  );
}

function Loading({ ticker }) {
  const stages = ['Waking the 18 masters…','Masters reading the financials…','Tallying bull & bear votes…','Sealing the prophecy…'];
  const [s, setS] = React.useState(0);
  React.useEffect(()=>{ const id=setInterval(()=>setS(p=>Math.min(p+1,stages.length-1)),650); return ()=>clearInterval(id); },[]);
  return (
    <div className="loading">
      <img src="../../assets/augur-owl-128.png" className="pixelated owl-spin" width="80" height="80"/>
      <div className="verdict neutral" style={{fontSize:'1rem',marginTop:'18px'}}>{ticker}</div>
      <div style={{font:'500 0.82rem/1 var(--font-mono)',color:'var(--amber)',marginTop:'10px'}}>{stages[s]}</div>
      <div className="gauge" style={{maxWidth:'240px',marginTop:'16px'}}><i style={{width:((s+1)/stages.length*100)+'%',transition:'width .6s'}}></i></div>
    </div>
  );
}

function StockAnalysis({ ticker, loading }) {
  const c = { ...window.CONSENSUS, ticker: ticker || 'NVDA' };
  if (loading) return <div style={{paddingTop:'24px'}}><Loading ticker={c.ticker}/></div>;
  const up = c.signal==='BULLISH';
  return (
    <div style={{paddingTop:'24px'}}>
      <div className="an-head">
        <div>
          <div style={{display:'flex',alignItems:'center',gap:'12px'}}>
            <span style={{font:'700 1.9rem/1 var(--font-mono)',color:'var(--fg-1)',letterSpacing:'-1px'}}>{c.ticker}</span>
            <span style={{font:'600 0.7rem/1 var(--font-pixfin)',color:'var(--fg-3)',textTransform:'uppercase'}}>{c.name}</span>
          </div>
          <div style={{display:'flex',alignItems:'center',gap:'10px',marginTop:'8px'}}>
            <span style={{font:'var(--data-lg)',color:'var(--fg-1)'}}>${c.price}</span>
            <span className={'signal-badge '+(up?'buy':'sell')}>{up?'▲ +2.41%':'▼ -1.1%'}</span>
          </div>
        </div>
        <div style={{display:'flex',gap:'8px'}}>
          <button className="btn">↻ Re-run</button>
          <button className="btn btn-primary">⤓ Export</button>
        </div>
      </div>
      <ExecCard c={c}/>
      <OracleSays c={c}/>
      <ScorecardGrid/>
      <Debate c={c}/>
      <DeepReport c={c}/>
    </div>
  );
}
window.StockAnalysis = StockAnalysis;
