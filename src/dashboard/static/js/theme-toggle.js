/**
 * Augur Theme Toggle
 * ==================
 * - Detects system color-scheme preference
 * - Reads/writes persisted theme from localStorage (key: 'augur-theme')
 * - Toggles between dark / light via data-theme attribute on <html>
 * - Dispatches 'augur:theme-change' custom event for downstream widgets
 * - Exposes window.augurTheme for imperative read/toggle
 *
 * Load this script after colors_and_type.css is in the DOM.
 */
;(function () {
  'use strict';

  var STORAGE_KEY = 'augur-theme';
  var DATA_ATTR = 'data-theme';
  var DARK = 'dark';
  var LIGHT = 'light';

  var html = document.documentElement;

  /* ---- helpers ---- */

  function getSystemPreference() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return DARK;
    }
    return LIGHT;
  }

  function getStored() {
    try {
      var v = localStorage.getItem(STORAGE_KEY);
      if (v === DARK || v === LIGHT) return v;
    } catch (_) { /* private browsing */ }
    return null;
  }

  function persist(theme) {
    try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
  }

  function apply(theme) {
    // Remove legacy class-based theme flags
    html.classList.remove(DARK, LIGHT);

    // Set data-theme attribute (primary mechanism)
    if (theme === LIGHT) {
      html.setAttribute(DATA_ATTR, LIGHT);
      // Also keep legacy .light class for compatibility
      html.classList.add(LIGHT);
    } else {
      html.setAttribute(DATA_ATTR, DARK);
      html.classList.add(DARK);
    }
  }

  function getCurrent() {
    var attr = html.getAttribute(DATA_ATTR);
    if (attr === LIGHT) return LIGHT;
    return DARK;
  }

  function broadcast(theme) {
    try {
      window.dispatchEvent(new CustomEvent('augur:theme-change', {
        detail: { theme: theme },
        bubbles: false
      }));
    } catch (_) {}
  }

  /* ---- toggle ---- */

  function toggle() {
    var current = getCurrent();
    var next = current === DARK ? LIGHT : DARK;
    apply(next);
    persist(next);
    broadcast(next);
    updateFabIcon(next);
    return next;
  }

  /* ---- FAB icon update ---- */

  function updateFabIcon(theme) {
    var fab = document.querySelector('.theme-toggle-fab');
    if (!fab) return;
    var moon = fab.querySelector('.icon-moon');
    var sun = fab.querySelector('.icon-sun');
    if (moon && sun) {
      if (theme === DARK) {
        moon.style.display = 'none';
        sun.style.display = 'inline';
      } else {
        moon.style.display = 'inline';
        sun.style.display = 'none';
      }
    }
    // Also update sidebar inline button if present
    var icon = document.getElementById('theme-icon');
    if (icon) {
      icon.textContent = theme === DARK ? '\u2600\uFE0F' : '\uD83C\uDF19';
    }
    var label = document.getElementById('theme-label');
    if (label) {
      label.textContent = theme === DARK ? 'Light' : 'Dark';
    }
  }

  /* ---- init ---- */

  function init() {
    var stored = getStored();
    var theme;

    if (stored) {
      // User has explicitly chosen before
      theme = stored;
    } else {
      // First visit: use system preference
      theme = getSystemPreference();
    }

    apply(theme);
    updateFabIcon(theme);
    broadcast(theme);
  }

  // Listen for system preference changes when no explicit choice
  if (window.matchMedia) {
    try {
      var mql = window.matchMedia('(prefers-color-scheme: dark)');
      mql.addEventListener('change', function (e) {
        // Only auto-switch if user hasn't made an explicit choice
        if (getStored() === null) {
          var next = e.matches ? DARK : LIGHT;
          apply(next);
          updateFabIcon(next);
          broadcast(next);
        }
      });
    } catch (_) {}
  }

  /* ---- public API ---- */

  window.augurTheme = {
    get: getCurrent,
    set: function (theme) {
      if (theme !== DARK && theme !== LIGHT) return;
      apply(theme);
      persist(theme);
      updateFabIcon(theme);
      broadcast(theme);
    },
    toggle: toggle,
    init: init,
    DARK: DARK,
    LIGHT: LIGHT
  };

  // Auto-init on script load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
