/**
 * Augur Saved Research Views (H03)
 * ================================
 * Reusable localStorage-backed filter-view manager.
 *
 * Usage on any page:
 *   augurSavedViews.init({
 *     storageKey: 'augur-inbox-views',   // unique per page
 *     listElementId: 'saved-views-list',  // <ul> container
 *     captureState: function() { return { ticker: ..., type: ... }; },
 *     applyState:  function(state) { ... },
 *     onChanged:   function() { ... },    // optional, called after load/delete
 *   });
 *
 * Exposes window.augurSavedViews:
 *   .init(config)       — one-time setup
 *   .save(name)         — capture current state + persist
 *   .load(viewId)       — apply saved state
 *   .delete(viewId)     — remove one view
 *   .getViews()         — readonly list
 *   .getActiveViewId()  — currently active view id (or null)
 */

;(function () {
  'use strict';

  var _config = null;
  var _views = [];
  var _activeViewId = null;
  var _initialized = false;

  /* ---- localStorage helpers ---- */

  function _storageAvail() {
    try { var t = '__t__'; localStorage.setItem(t, '1'); localStorage.removeItem(t); return true; } catch (e) { return false; }
  }

  function _lsGet(key, fallback) {
    if (!_storageAvail()) return fallback;
    try { var v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
  }

  function _lsSet(key, val) {
    if (!_storageAvail()) return;
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
  }

  function _loadFromStorage() {
    _views = _lsGet(_config.storageKey, []);
  }

  function _saveToStorage() {
    _lsSet(_config.storageKey, _views);
  }

  /* ---- rendering ---- */

  function renderList() {
    var list = document.getElementById(_config.listElementId);
    if (!list) return;
    if (_views.length === 0) {
      list.innerHTML = '<li class="text-muted" style="font-size:0.72rem; padding:6px 0;">No saved views yet</li>';
      return;
    }
    var html = '';
    _views.forEach(function (view) {
      var activeClass = view.id === _activeViewId ? ' active' : '';
      html += '<li class="saved-view-item' + activeClass + '" onclick="augurSavedViews.load(\'' + view.id + '\')" role="button" tabindex="0" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();augurSavedViews.load(\'' + view.id + '\')}">' +
        '<span class="view-name" title="' + _escapeHtml(view.name) + '">' + _escapeHtml(view.name) + '</span>' +
        '<button class="view-delete" onclick="augurSavedViews.delete(\'' + view.id + '\', event)" aria-label="Delete view ' + _escapeHtml(view.name) + '" title="Delete">&times;</button>' +
        '</li>';
    });
    list.innerHTML = html;
  }

  function _escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  /* ---- public API ---- */

  var api = {
    /** Initialize saved views for this page. Call once on DOMContentLoaded. */
    init: function (config) {
      if (_initialized) return;
      _config = config;
      _loadFromStorage();
      _initialized = true;
      renderList();

      // Wire up Enter key on the save input if present
      var input = document.getElementById('save-view-name');
      if (input && !input._svWired) {
        input._svWired = true;
        input.addEventListener('keydown', function (e) {
          if (e.key === 'Enter') api.saveFromInput();
        });
      }
    },

    /** Save current filter state under a name (from the page's save input). */
    saveFromInput: function () {
      var nameInput = document.getElementById('save-view-name');
      var name = (nameInput ? nameInput.value : '').trim();
      if (!name) {
        if (typeof showToast === 'function') showToast('Please enter a view name', 'warning');
        return;
      }
      api.save(name);
      if (nameInput) nameInput.value = '';
    },

    /** Save current state with the given name. */
    save: function (name) {
      if (!_config || !_config.captureState) return;
      var state = _config.captureState();
      var id = 'view-' + Date.now();

      _views.push({ id: id, name: name, state: state });
      _saveToStorage();
      _activeViewId = id;
      renderList();
      if (typeof showToast === 'function') showToast('View "' + name + '" saved', 'success');
      if (_config.onChanged) _config.onChanged();
    },

    /** Load and apply a saved view by id. */
    load: function (viewId) {
      var view = _views.find(function (v) { return v.id === viewId; });
      if (!view) return;
      _activeViewId = viewId;
      if (_config.applyState) _config.applyState(view.state);
      renderList();
    },

    /** Delete a saved view by id. Pass the click event as second arg to stop propagation. */
    delete: function (viewId, e) {
      if (e) { e.stopPropagation(); e.preventDefault(); }
      _views = _views.filter(function (v) { return v.id !== viewId; });
      if (_activeViewId === viewId) _activeViewId = null;
      _saveToStorage();
      renderList();
      if (_config.onChanged) _config.onChanged();
    },

    /** Mark no view active (e.g. when user changes filters manually). */
    clearActive: function () {
      _activeViewId = null;
      renderList();
    },

    /** Return the currently active view id, or null. */
    getActiveViewId: function () {
      return _activeViewId;
    },

    /** Return a shallow copy of all saved views. */
    getViews: function () {
      return _views.slice();
    }
  };

  window.augurSavedViews = api;
})();
