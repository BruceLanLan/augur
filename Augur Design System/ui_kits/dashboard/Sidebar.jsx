/* Augur UI Kit — Sidebar (Bloomberg rail + HD-2D owl crest) */
const { useState } = React;

const IC= {
  dash:  <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>,
  stocks:<svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M18 9l-5 5-2-2-4 4"/></svg>,
  signals:<svg viewBox="0 0 24 24"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>,
  scanner:<svg viewBox="0 0 24 24"><path d="M3 3h18v18H3z"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18" opacity="0.5" strokeWidth="1"/></svg>,
  watch: <svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>,
  port:  <svg viewBox="0 0 24 24"><path d="M2 7a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7z"/><path d="M16 3v4M8 3v4M2 11h20"/></svg>,
  back:  <svg viewBox="0 0 24 24"><path d="M12 8v4l3 3"/><circle cx="12" cy="12" r="9"/></svg>,
  chat:  <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>,
  people:<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
  plus:  <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>,
  cog:   <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
};

function NavItem({ icon, label, badge, active, onClick }) {
  return (
    <a className={'sb-item' + (active ? ' active' : '')} onClick={onClick}>
      {icon}<span>{label}</span>{badge && <em className="sb-badge">{badge}</em>}
    </a>
  );
}

function Sidebar({ page, go }) {
  return (
    <aside className="sb bg-grid">
      <div className="sb-logo" onClick={() => go('home')}>
        <img src="../../assets/augur-owl-64.png" className="pixelated" width="32" height="32" alt="Augur"/>
        <span className="sb-word">Augur</span>
      </div>

      <nav className="sb-nav">
        <div className="sb-group">Analysis</div>
        <NavItem icon={ICdict('dash')}   label="Dashboard"   active={page==='home'}    onClick={()=>go('home')} />
        <NavItem icon={ICdict('stocks')} label="Stock Analysis" active={page==='stocks'} onClick={()=>go('stocks')} />
        <NavItem icon={ICdict('signals')} label="Signals" badge="LIVE" onClick={()=>go('home')} />
        <NavItem icon={ICdict('scanner')} label="Scanner" onClick={()=>go('home')} />
        <NavItem icon={ICdict('watch')}  label="Watchlist" onClick={()=>go('home')} />
        <NavItem icon={ICdict('port')}   label="Portfolio" onClick={()=>go('home')} />
        <NavItem icon={ICdict('back')}   label="Backtest" onClick={()=>go('home')} />

        <div className="sb-group">The Council</div>
        <NavItem icon={ICdict('people')} label="18 Masters" active={page==='council'} onClick={()=>go('council')} />
        <NavItem icon={ICdict('chat')}   label="Consult (Chat)" onClick={()=>go('council')} />
        <NavItem icon={ICdict('plus')}   label="Summon New" onClick={()=>go('council')} />

        <div className="sb-group">System</div>
        <NavItem icon={ICdict('cog')}    label="Settings" onClick={()=>go('home')} />
      </nav>

      <div className="sb-foot">
        <div className="sb-status"><span className="dot live"></span><span>Oracle online · yfinance live</span></div>
        <div className="sb-ver">AUGUR v8.1.0</div>
      </div>
    </aside>
  );
}
function ICdict(k){ return IC[k]; }

window.Sidebar = Sidebar;
window.AUG_IC = IC;
