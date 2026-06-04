/* Augur UI Kit — The Council (masters roster) */
function MasterDetail({ m, onClose }) {
  if (!m) return null;
  const s = window.SCHOOLS[m.school];
  return (
    <div className="overlay" onClick={onClose}>
      <div className="detail gilt-edge" onClick={e=>e.stopPropagation()}>
        <button className="detail-x" onClick={onClose}>✕</button>
        <div className="detail-top">
          <div className="detail-medallion"><div className="disc"><img src={'../../assets/avatars/'+m.id+'.png'} alt={m.name}/></div><div className="crest">{s.glyph}</div></div>
          <div>
            <div className="t-eyebrow" style={{color:s.color}}>{s.glyph} {s.label}</div>
            <div style={{font:'700 1.25rem/1.1 var(--font-pixfin)',color:'var(--fg-1)',margin:'8px 0 2px'}}>{m.name}</div>
            <div style={{font:'600 0.8rem/1 var(--font-mono)',color:'var(--fg-3)'}}>{m.zh}</div>
            <div style={{display:'flex',gap:'18px',marginTop:'14px'}}>
              <div className="aug-stat"><span className="l">Last Score</span><span className="v">{m.score}</span></div>
              <div className="aug-stat"><span className="l">Signal</span><span className="v"><span className={'signal-badge '+m.sig}>{m.sig.toUpperCase()}</span></span></div>
            </div>
          </div>
        </div>
        <div className="dialogue" style={{marginTop:'18px'}}>
          <div className="speaker"><img src={'../../assets/avatars/'+m.id+'.png'} className="avatar" width="20" height="20"/> {m.name}</div>
          <div>&ldquo;My edge is <b style={{color:'var(--gilt-bright)'}}>{m.framework}</b>. I am at my strongest in: {m.best}.&rdquo;</div>
          <span className="chevron">▼</span>
        </div>
        <div style={{display:'flex',gap:'8px',marginTop:'16px'}}>
          <button className="pixel-btn">▶ Consult on a ticker</button>
          <button className="pixel-btn dark">Add to duel</button>
        </div>
      </div>
    </div>
  );
}

function Council() {
  const [filter, setFilter] = React.useState('all');
  const [sel, setSel] = React.useState(null);
  const schools = Object.entries(window.SCHOOLS);
  const list = filter==='all' ? window.MASTERS : window.MASTERS.filter(m=>m.school===filter);
  return (
    <div style={{paddingTop:'24px'}}>
      <div className="council-hero gilt-edge">
        <img src="../../assets/augur-owl-128.png" className="pixelated" width="64" height="64"/>
        <div>
          <div className="t-eyebrow" style={{color:'var(--gilt)'}}>▸ The Council of Masters</div>
          <h1 style={{font:'var(--h1)',color:'var(--fg-1)',margin:'6px 0 4px'}}>Eighteen legends. One verdict.</h1>
          <p style={{font:'var(--body-sm)',color:'var(--fg-2)',margin:0,maxWidth:'520px'}}>Each master scores independently through their own framework. The council weights every voice into a single Kelly-sized consensus.</p>
        </div>
      </div>

      <div className="filters">
        <button className={'filter-tag'+(filter==='all'?' active':'')} onClick={()=>setFilter('all')}>All · {window.MASTERS.length}</button>
        {schools.map(([k,s])=>(
          <button key={k} className={'filter-tag'+(filter===k?' active':'')} onClick={()=>setFilter(k)}>{s.glyph} {s.label}</button>
        ))}
      </div>

      <div className="council-grid">
        {list.map(m=>{
          const s = window.SCHOOLS[m.school];
          const pips = Math.max(1, Math.round(m.score/2));
          return (
            <div key={m.id} className="mcard" onClick={()=>setSel(m)}>
              <div className="medallion"><div className="disc"><img src={'../../assets/avatars/'+m.id+'.png'} alt={m.name}/></div><div className="crest">{s.glyph}</div></div>
              <div className="mplate">{m.name}</div>
              <div className="mzh" style={{color:s.color}}>{m.zh} · {s.label}</div>
              <div className="mstats">
                <span className="sc">{m.score}<small>/10</small></span>
                <span className="conv">{'\u25CF'.repeat(pips)}<span className="off">{'\u25CF'.repeat(5-pips)}</span></span>
              </div>
            </div>
          );
        })}
      </div>
      <MasterDetail m={sel} onClose={()=>setSel(null)}/>
    </div>
  );
}
window.Council = Council;
