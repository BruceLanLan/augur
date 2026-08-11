/**
 * Augur Command Palette — universal ⌘K search for Dashboard.
 *
 * Usage: press ⌘K / Ctrl+K anywhere in the Dashboard to open.
 * Type to filter actions, Enter to execute, Esc to close.
 *
 * Actions are defined in window.__AUGUR_COMMANDS__ or fall back to defaults.
 */

(function () {
  'use strict';

  const DEFAULT_COMMANDS = [
    { id: 'analyze', label: 'Analyze Stock', shortcut: 'A', icon: '📊', action: function () { window.location = '/stocks'; } },
    { id: 'committee', label: 'Investment Committee', shortcut: 'C', icon: '🏛️', action: function () { window.location = '/committee'; } },
    { id: 'debate', label: 'Bull vs Bear Debate', shortcut: 'D', icon: '⚔️', action: function () { window.location = '/debate'; } },
    { id: 'compare', label: 'Compare Personas', shortcut: 'P', icon: '📈', action: function () { window.location = '/compare'; } },
    { id: 'history', label: 'Research History', shortcut: 'H', icon: '📅', action: function () { window.location = '/history'; } },
    { id: 'watchlist', label: 'Watchlist', shortcut: 'W', icon: '⭐', action: function () { window.location = '/watchlist'; } },
    { id: 'portfolio', label: 'Portfolio Review', shortcut: 'O', icon: '💼', action: function () { window.location = '/portfolio'; } },
    { id: 'settings', label: 'Settings & Workspace', shortcut: 'S', icon: '⚙️', action: function () { window.location = '/settings'; } },
    { id: 'personas', label: 'Manage Personas', shortcut: 'M', icon: '🎭', action: function () { window.location = '/personas'; } },
    { id: 'backtest', label: 'Run Backtest', shortcut: 'B', icon: '⏪', action: function () { window.location = '/backtest'; } },
    { id: 'skills', label: 'Research Skills (earnings-prep, filing-delta)', shortcut: 'K', icon: '🔬', action: function () { window.location = '/scanner'; } },
    { id: 'evidence', label: 'Evidence Explorer', shortcut: 'E', icon: '📋', action: function () { window.location = '/history'; } },
    { id: 'thesis', label: 'Thesis Journal', shortcut: 'T', icon: '📝', action: function () { window.location = '/history'; } },
    { id: 'export', label: 'Export Report', shortcut: 'X', icon: '📤', action: function () { window.location = '/report_view'; } },
    { id: 'valuation', label: 'DCF Valuation Lab', shortcut: 'V', icon: '🔢', action: function () { window.location = '/optimizer'; } },
  ];

  var commands = window.__AUGUR_COMMANDS__ || DEFAULT_COMMANDS;
  var overlay = null;
  var input = null;
  var list = null;
  var selectedIndex = -1;

  function create() {
    overlay = document.createElement('div');
    overlay.id = 'augur-cmd-palette';
    overlay.innerHTML = '<div class="acp-backdrop"></div>'
      + '<div class="acp-dialog">'
      + '  <div class="acp-header">'
      + '    <input class="acp-input" type="text" placeholder="Type a command..." autofocus>'
      + '    <span class="acp-hint">⌘K</span>'
      + '  </div>'
      + '  <ul class="acp-list"></ul>'
      + '  <div class="acp-footer">'
      + '    <span>↑↓ navigate</span><span>↵ execute</span><span>Esc close</span>'
      + '  </div>'
      + '</div>';
    document.body.appendChild(overlay);

    input = overlay.querySelector('.acp-input');
    list = overlay.querySelector('.acp-list');

    input.addEventListener('input', filter);
    input.addEventListener('keydown', navigate);
    overlay.querySelector('.acp-backdrop').addEventListener('click', close);
  }

  function filter() {
    var q = input.value.toLowerCase().trim();
    var filtered = q
      ? commands.filter(function (c) { return c.label.toLowerCase().indexOf(q) !== -1 || c.id.indexOf(q) !== -1; })
      : commands;

    list.innerHTML = '';
    selectedIndex = -1;

    filtered.forEach(function (cmd, i) {
      var li = document.createElement('li');
      li.className = 'acp-item';
      li.innerHTML = '<span class="acp-icon">' + (cmd.icon || '•') + '</span>'
        + '<span class="acp-label">' + cmd.label + '</span>'
        + (cmd.shortcut ? '<kbd class="acp-shortcut">' + cmd.shortcut + '</kbd>' : '');
      li.addEventListener('click', function () { execute(cmd); });
      li.addEventListener('mouseenter', function () { select(i); });
      list.appendChild(li);
    });

    if (filtered.length > 0) select(0);
  }

  function navigate(e) {
    var items = list.querySelectorAll('.acp-item');
    if (e.key === 'ArrowDown') { e.preventDefault(); select(selectedIndex + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); select(selectedIndex - 1); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      var sel = list.querySelector('.acp-item.active');
      if (sel) sel.click();
    }
    else if (e.key === 'Escape') { close(); }
  }

  function select(i) {
    var items = list.querySelectorAll('.acp-item');
    items.forEach(function (el) { el.classList.remove('active'); });
    selectedIndex = Math.max(0, Math.min(i, items.length - 1));
    var el = items[selectedIndex];
    if (el) { el.classList.add('active'); el.scrollIntoView({ block: 'nearest' }); }
  }

  function execute(cmd) {
    close();
    if (typeof cmd.action === 'function') cmd.action();
  }

  function open() {
    if (!overlay) create();
    overlay.style.display = 'flex';
    input.value = '';
    filter();
    setTimeout(function () { input.focus(); }, 50);
  }

  function close() {
    if (overlay) overlay.style.display = 'none';
  }

  // Keyboard shortcut
  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (overlay && overlay.style.display === 'flex') close();
      else open();
    }
  });
})();
