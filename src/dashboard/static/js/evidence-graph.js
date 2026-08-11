/**
 * Augur Evidence Graph — lightweight force-directed graph (pure JS, no D3.js)
 *
 * Nodes: Claim (rounded rect) + EvidenceItem (circle)
 * Edges: supports (green) / contradicts (red) / insufficient (gray dashed)
 * Canvas rendering with hover highlight and click detail panel.
 * Nodes <  50 → force-directed layout
 * Nodes >= 50 → degrades to a sorted list view
 *
 * Usage:
 *   const graph = new EvidenceGraph(containerEl, {
 *     nodes: [...],
 *     edges: [...],
 *     onNodeClick: function(node) { ... }
 *   });
 *   graph.start();
 *
 * @module evidence-graph
 * @version 1.0.0
 */
(function (global) {
  'use strict';

  /* ================================================================
     Constants
     ================================================================ */
  var NODE_RADIUS_CLAIM = 8;       // Claim node corner radius
  var NODE_RADIUS_EVIDENCE = 18;   // EvidenceItem node radius
  var NODE_WIDTH_CLAIM = 140;
  var NODE_HEIGHT_CLAIM = 36;

  var EDGE_COLORS = {
    supports:      '#00c853',
    contradicts:   '#ff1744',
    insufficient:  '#666666'
  };

  var NODE_COLORS = {
    claim:         '#ff8c00',
    evidenceItem:  '#5cc8ff'
  };

  var FORCE_THRESHOLD = 50;  // degrade to list beyond this

  /* ================================================================
     Force-directed simulation
     ================================================================ */
  function forceSimulation(nodes, edges, width, height) {
    var alpha = 1;
    var alphaDecay = 0.02;
    var alphaMin = 0.001;
    var velocityDecay = 0.4;

    var repulsionStrength = 600;
    var attractionStrength = 0.005;
    var centerStrength = 0.05;
    var maxVelocity = 8;
    var maxIterations = 300;

    // Initialise positions if missing
    nodes.forEach(function (n, i) {
      if (n.x === undefined) n.x = width / 2 + (Math.random() - 0.5) * width * 0.4;
      if (n.y === undefined) n.y = height / 2 + (Math.random() - 0.5) * height * 0.4;
      n.vx = 0;
      n.vy = 0;
    });

    var iter = 0;
    while (alpha > alphaMin && iter < maxIterations) {
      iter++;
      alpha += (alphaMin - alpha) * alphaDecay;

      // Repulsion between all node pairs
      for (var i = 0; i < nodes.length; i++) {
        var a = nodes[i];
        for (var j = i + 1; j < nodes.length; j++) {
          var b = nodes[j];
          var dx = b.x - a.x;
          var dy = b.y - a.y;
          var dist = Math.sqrt(dx * dx + dy * dy) || 1;
          var force = (repulsionStrength * alpha) / (dist * dist);
          var fx = (dx / dist) * force;
          var fy = (dy / dist) * force;
          a.vx -= fx;
          a.vy -= fy;
          b.vx += fx;
          b.vy += fy;
        }
      }

      // Attraction along edges
      for (var e = 0; e < edges.length; e++) {
        var edge = edges[e];
        var source = edge.source;
        var target = edge.target;
        if (!source || !target) continue;
        var dx = target.x - source.x;
        var dy = target.y - source.y;
        var dist = Math.sqrt(dx * dx + dy * dy) || 1;
        var force = dist * attractionStrength * alpha;
        var fx = (dx / dist) * force;
        var fy = (dy / dist) * force;
        source.vx += fx;
        source.vy += fy;
        target.vx -= fx;
        target.vy -= fy;
      }

      // Center gravity
      for (var k = 0; k < nodes.length; k++) {
        var n = nodes[k];
        n.vx += (width / 2 - n.x) * centerStrength * alpha;
        n.vy += (height / 2 - n.y) * centerStrength * alpha;
      }

      // Apply velocities with decay
      for (var m = 0; m < nodes.length; m++) {
        var node = nodes[m];
        node.vx *= velocityDecay;
        node.vy *= velocityDecay;
        // Clamp velocity
        var speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
        if (speed > maxVelocity) {
          node.vx = (node.vx / speed) * maxVelocity;
          node.vy = (node.vy / speed) * maxVelocity;
        }
        node.x += node.vx;
        node.y += node.vy;
        // Keep within bounds with padding
        var pad = 30;
        node.x = Math.max(pad, Math.min(width - pad, node.x));
        node.y = Math.max(pad, Math.min(height - pad, node.y));
      }
    }
  }

  /* ================================================================
     EvidenceGraph class
     ================================================================ */
  function EvidenceGraph(container, opts) {
    opts = opts || {};
    this.container = container;
    this.nodes = (opts.nodes || []).slice();
    this.edges = (opts.edges || []).slice();
    this.onNodeClick = opts.onNodeClick || null;
    this.width = 0;
    this.height = 0;
    this.dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
    this.hoveredNode = null;
    this.selectedNode = null;
    this.animationId = null;
    this._simulated = false;
    this._listMode = this.nodes.length >= FORCE_THRESHOLD;

    this._build();
  }

  EvidenceGraph.prototype = {
    _build: function () {
      var self = this;
      var container = this.container;

      // Clear container
      container.innerHTML = '';

      if (!this.nodes.length) {
        container.innerHTML =
          '<div class="evidence-graph-placeholder">' +
          '<span class="placeholder-icon">&#x1F4CA;</span>' +
          '<span>No evidence graph data available</span>' +
          '</div>';
        return;
      }

      // Canvas
      this.canvas = document.createElement('canvas');
      this.canvas.style.display = 'block';
      this.canvas.style.width = '100%';
      this.canvas.style.height = '100%';
      container.appendChild(this.canvas);

      // Tooltip
      this.tooltip = document.createElement('div');
      this.tooltip.className = 'graph-tooltip';
      this.tooltip.setAttribute('aria-hidden', 'true');
      container.appendChild(this.tooltip);

      // Detail panel
      this.detailPanel = document.createElement('div');
      this.detailPanel.className = 'graph-detail-panel';
      container.appendChild(this.detailPanel);

      // Bind events
      this.canvas.addEventListener('mousemove', function (e) { self._onMouseMove(e); });
      this.canvas.addEventListener('mouseleave', function () { self._onMouseLeave(); });
      this.canvas.addEventListener('click', function (e) { self._onClick(e); });

      // Resize observer
      if (typeof ResizeObserver !== 'undefined') {
        this._resizeObserver = new ResizeObserver(function () { self._resize(); });
        this._resizeObserver.observe(this.canvas);
      }

      this._resize();
    },

    _resize: function () {
      var rect = this.canvas.getBoundingClientRect();
      this.width = rect.width;
      this.height = rect.height || 420;
      this.canvas.width = this.width * this.dpr;
      this.canvas.height = this.height * this.dpr;

      if (!this._simulated && !this._listMode) {
        forceSimulation(this.nodes, this.edges, this.width, this.height);
        this._simulated = true;
      }
      this._draw();
    },

    /* ---- Drawing ---- */
    _draw: function () {
      var ctx = this.canvas.getContext('2d');
      var w = this.width;
      var h = this.height;
      var dpr = this.dpr;

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, w, h);

      // Background
      ctx.fillStyle = 'rgba(0,0,0,0)';
      ctx.fillRect(0, 0, w, h);

      if (this._listMode) {
        this._drawList(ctx, w, h);
      } else {
        this._drawEdges(ctx);
        this._drawNodes(ctx);
      }

      ctx.restore();
    },

    _drawEdges: function (ctx) {
      var self = this;
      this.edges.forEach(function (edge) {
        var source = edge.source;
        var target = edge.target;
        if (!source || !target) return;

        var color = EDGE_COLORS[edge.relation] || EDGE_COLORS.insufficient;
        var isInsufficient = edge.relation === 'insufficient';
        var isHighlighted =
          self.hoveredNode &&
          (source.id === self.hoveredNode.id || target.id === self.hoveredNode.id);

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);

        if (isInsufficient) {
          ctx.setLineDash([4, 6]);
        }
        ctx.strokeStyle = isHighlighted ? color : color.replace(')', ',0.35)').replace('rgb', 'rgba');
        if (color.indexOf('#') === 0) {
          ctx.strokeStyle = isHighlighted ? color : color + '59'; // 35% opacity hex
        }
        ctx.lineWidth = isHighlighted ? 2 : 1;
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
      });
    },

    _drawNodes: function (ctx) {
      var self = this;
      this.nodes.forEach(function (node) {
        var isHovered = self.hoveredNode && self.hoveredNode.id === node.id;
        var isSelected = self.selectedNode && self.selectedNode.id === node.id;

        if (node.type === 'evidenceItem') {
          self._drawEvidenceNode(ctx, node, isHovered, isSelected);
        } else {
          self._drawClaimNode(ctx, node, isHovered, isSelected);
        }
      });
    },

    _drawClaimNode: function (ctx, node, isHovered, isSelected) {
      var x = node.x;
      var y = node.y;
      var w = NODE_WIDTH_CLAIM;
      var h = NODE_HEIGHT_CLAIM;
      var r = NODE_RADIUS_CLAIM;
      var rx = x - w / 2;
      var ry = y - h / 2;

      ctx.save();

      // Shadow on hover/select
      if (isHovered || isSelected) {
        ctx.shadowColor = 'rgba(255,140,0,0.35)';
        ctx.shadowBlur = 12;
      }

      // Fill
      ctx.fillStyle = isHovered || isSelected
        ? 'rgba(255,140,0,0.2)'
        : 'rgba(255,140,0,0.1)';
      ctx.beginPath();
      ctx.moveTo(rx + r, ry);
      ctx.lineTo(rx + w - r, ry);
      ctx.arcTo(rx + w, ry, rx + w, ry + r, r);
      ctx.lineTo(rx + w, ry + h - r);
      ctx.arcTo(rx + w, ry + h, rx + w - r, ry + h, r);
      ctx.lineTo(rx + r, ry + h);
      ctx.arcTo(rx, ry + h, rx, ry + h - r, r);
      ctx.lineTo(rx, ry + r);
      ctx.arcTo(rx, ry, rx + r, ry, r);
      ctx.closePath();
      ctx.fill();

      // Border
      ctx.strokeStyle = isHovered || isSelected
        ? 'rgba(255,140,0,0.8)'
        : 'rgba(255,140,0,0.4)';
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.stroke();

      ctx.shadowColor = 'transparent';

      // Label
      var label = (node.label || node.id || '').substring(0, 16);
      ctx.fillStyle = isHovered ? '#ffaa33' : '#ff8c00';
      ctx.font = '600 10px ' + getComputedStyle(document.documentElement)
        .getPropertyValue('--font-sans').replace(/'/g, '').split(',')[0] || 'Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x, y);

      ctx.restore();
    },

    _drawEvidenceNode: function (ctx, node, isHovered, isSelected) {
      var x = node.x;
      var y = node.y;
      var r = isHovered ? NODE_RADIUS_EVIDENCE + 2 : NODE_RADIUS_EVIDENCE;

      ctx.save();

      if (isHovered || isSelected) {
        ctx.shadowColor = 'rgba(92,200,255,0.35)';
        ctx.shadowBlur = 10;
      }

      // Fill
      ctx.fillStyle = isHovered || isSelected
        ? 'rgba(92,200,255,0.25)'
        : 'rgba(92,200,255,0.12)';
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();

      // Border
      ctx.strokeStyle = isHovered || isSelected
        ? 'rgba(92,200,255,0.8)'
        : 'rgba(92,200,255,0.45)';
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.stroke();

      ctx.shadowColor = 'transparent';

      // Label (short)
      var label = (node.label || node.id || '').substring(0, 8);
      ctx.fillStyle = isHovered ? '#5cc8ff' : '#4db6e0';
      ctx.font = '500 9px ' + (getComputedStyle(document.documentElement)
        .getPropertyValue('--font-mono').replace(/'/g, '').split(',')[0] || 'JetBrains Mono, monospace');
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, x, y);

      ctx.restore();
    },

    /* ---- List mode fallback ---- */
    _drawList: function (ctx, w, h) {
      var self = this;
      var rowH = 32;
      var startY = 20;
      var leftColX = 24;
      var rightColX = w * 0.45;

      ctx.fillStyle = '#8888a0';
      ctx.font = '600 11px ' + (getComputedStyle(document.documentElement)
        .getPropertyValue('--font-sans').replace(/'/g, '').split(',')[0] || 'Inter, sans-serif');
      ctx.textAlign = 'left';
      ctx.fillText('Evidence Graph (' + this.nodes.length + ' nodes — list view)', leftColX, startY);

      // Separator line
      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(leftColX, startY + 8);
      ctx.lineTo(w - leftColX, startY + 8);
      ctx.stroke();

      var colX = leftColX;
      var colW = (w - leftColX * 2) / 2;
      var itemH = 36;

      this.nodes.forEach(function (node, i) {
        var col = i % 2;
        var row = Math.floor(i / 2);
        var x = colX + col * colW;
        var y = startY + 24 + row * itemH;

        // Hit-test rect for hover/click
        node._listRect = { x: x, y: y - 10, w: colW - 12, h: itemH - 4 };

        var isHovered = self.hoveredNode && self.hoveredNode.id === node.id;
        var isSelected = self.selectedNode && self.selectedNode.id === node.id;

        // Row background
        if (isHovered || isSelected) {
          ctx.fillStyle = isSelected
            ? 'rgba(255,140,0,0.12)'
            : 'rgba(255,255,255,0.03)';
          ctx.beginPath();
          ctx.roundRect(node._listRect.x, node._listRect.y, node._listRect.w, node._listRect.h, 4);
          ctx.fill();
        }

        // Type indicator
        if (node.type === 'evidenceItem') {
          ctx.fillStyle = isHovered ? '#5cc8ff' : '#4db6e0';
          ctx.beginPath();
          ctx.arc(x + 8, y, 6, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillStyle = isHovered ? '#ffaa33' : '#ff8c00';
          ctx.beginPath();
          ctx.roundRect(x + 2, y - 5, 12, 10, 2);
          ctx.fill();
        }

        // Label
        ctx.fillStyle = isHovered ? '#e8e8f0' : '#8888a0';
        ctx.font = '500 10px ' + (getComputedStyle(document.documentElement)
          .getPropertyValue('--font-mono').replace(/'/g, '').split(',')[0] || 'JetBrains Mono, monospace');
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText((node.label || node.id || '').substring(0, 28), x + 22, y);
      });
    },

    /* ---- Interaction ---- */
    _hitTest: function (mouseX, mouseY) {
      if (this._listMode) {
        for (var i = 0; i < this.nodes.length; i++) {
          var r = this.nodes[i]._listRect;
          if (r && mouseX >= r.x && mouseX <= r.x + r.w &&
              mouseY >= r.y && mouseY <= r.y + r.h) {
            return this.nodes[i];
          }
        }
        return null;
      }

      for (var j = this.nodes.length - 1; j >= 0; j--) {
        var node = this.nodes[j];
        var dx = mouseX - node.x;
        var dy = mouseY - node.y;
        var threshold = node.type === 'evidenceItem'
          ? NODE_RADIUS_EVIDENCE + 4
          : Math.max(NODE_WIDTH_CLAIM / 2, NODE_HEIGHT_CLAIM / 2) + 4;
        if (Math.sqrt(dx * dx + dy * dy) < threshold) {
          return node;
        }
      }
      return null;
    },

    _onMouseMove: function (e) {
      var rect = this.canvas.getBoundingClientRect();
      var mx = e.clientX - rect.left;
      var my = e.clientY - rect.top;
      var node = this._hitTest(mx, my);

      if (node !== this.hoveredNode) {
        this.hoveredNode = node;
        this.canvas.style.cursor = node ? 'pointer' : 'default';

        // Update tooltip
        if (node) {
          this.tooltip.textContent = (node.label || node.id || '') +
            (node.detail ? ' — ' + node.detail.substring(0, 60) : '');
          this.tooltip.style.left = (mx + 16) + 'px';
          this.tooltip.style.top = my + 'px';
          this.tooltip.classList.add('visible');
        } else {
          this.tooltip.classList.remove('visible');
        }

        this._draw();
      } else if (node) {
        // Move tooltip
        this.tooltip.style.left = (mx + 16) + 'px';
        this.tooltip.style.top = my + 'px';
      }
    },

    _onMouseLeave: function () {
      this.hoveredNode = null;
      this.tooltip.classList.remove('visible');
      this.canvas.style.cursor = 'default';
      this._draw();
    },

    _onClick: function (e) {
      var rect = this.canvas.getBoundingClientRect();
      var mx = e.clientX - rect.left;
      var my = e.clientY - rect.top;
      var node = this._hitTest(mx, my);

      if (node) {
        this.selectedNode = (this.selectedNode && this.selectedNode.id === node.id)
          ? null
          : node;
        this._showDetail(node);
        this._draw();

        if (this.onNodeClick) {
          this.onNodeClick(node);
        }
      }
    },

    _showDetail: function (node) {
      if (!node) {
        this.detailPanel.classList.remove('open');
        this.detailPanel.innerHTML = '';
        return;
      }

      var typeLabel = node.type === 'claim' ? 'Claim' : 'Evidence Item';
      var html =
        '<button type="button" class="graph-detail-panel__close" ' +
        'onclick="this.parentElement.classList.remove(\'open\')" ' +
        'aria-label="Close">&times;</button>' +
        '<div class="graph-detail-panel__title">' +
        escapeHtml(typeLabel) + ': ' + escapeHtml(node.label || node.id || '') +
        '</div>' +
        '<div class="graph-detail-panel__body">' +
        (node.detail ? '<p>' + escapeHtml(node.detail) + '</p>' : '<p>No additional details.</p>') +
        (node.source ? '<p style="margin-top:8px;"><strong>Source:</strong> ' + escapeHtml(node.source) + '</p>' : '') +
        (node.calibration ? '<p style="margin-top:4px;"><span class="calib-badge calib-badge--' +
          escapeAttr(node.calibration) + '">' +
          '<span class="calib-badge__dot"></span>' +
          escapeHtml(node.calibration) + '</span></p>' : '') +
        '</div>';

      this.detailPanel.innerHTML = html;
      this.detailPanel.classList.add('open');
    },

    /* ---- Public API ---- */
    start: function () {
      if (!this._listMode) {
        if (!this._simulated) {
          forceSimulation(this.nodes, this.edges, this.width || 600, this.height || 420);
          this._simulated = true;
        }
      }
      this._draw();
    },

    updateData: function (nodes, edges) {
      this.nodes = (nodes || []).slice();
      this.edges = (edges || []).slice();
      this._listMode = this.nodes.length >= FORCE_THRESHOLD;
      this._simulated = false;
      this.hoveredNode = null;
      this.selectedNode = null;
      this._build();
      this.start();
    },

    destroy: function () {
      if (this._resizeObserver) {
        this._resizeObserver.disconnect();
        this._resizeObserver = null;
      }
      if (this.animationId) {
        cancelAnimationFrame(this.animationId);
        this.animationId = null;
      }
      if (this.container) {
        this.container.innerHTML = '';
      }
    }
  };

  /* ---- Helpers ---- */
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function escapeAttr(str) {
    if (!str) return '';
    return String(str).replace(/[^a-zA-Z0-9_-]/g, '');
  }

  /* ================================================================
     Exports
     ================================================================ */
  global.EvidenceGraph = EvidenceGraph;

})(typeof window !== 'undefined' ? window : this);

// ============ Interaction enhancements ============

(function () {
  'use strict';
  var canvas = document.getElementById('evidence-graph-canvas');
  if (!canvas) return;

  var ctx = canvas.getContext('2d');
  var scale = 1, offsetX = 0, offsetY = 0;
  var isDragging = false, dragStartX = 0, dragStartY = 0;

  // Zoom with mouse wheel
  canvas.addEventListener('wheel', function (e) {
    e.preventDefault();
    var delta = e.deltaY > 0 ? 0.9 : 1.1;
    var rect = canvas.getBoundingClientRect();
    var mx = e.clientX - rect.left;
    var my = e.clientY - rect.top;
    offsetX = mx - delta * (mx - offsetX);
    offsetY = my - delta * (my - offsetY);
    scale *= delta;
    scale = Math.max(0.3, Math.min(3, scale));
  }, { passive: false });

  // Pan with mouse drag
  canvas.addEventListener('mousedown', function (e) {
    isDragging = true;
    dragStartX = e.clientX - offsetX;
    dragStartY = e.clientY - offsetY;
    canvas.style.cursor = 'grabbing';
  });
  canvas.addEventListener('mousemove', function (e) {
    if (!isDragging) return;
    offsetX = e.clientX - dragStartX;
    offsetY = e.clientY - dragStartY;
  });
  canvas.addEventListener('mouseup', function () {
    isDragging = false;
    canvas.style.cursor = 'grab';
  });
  canvas.addEventListener('mouseleave', function () {
    isDragging = false;
    canvas.style.cursor = 'grab';
  });

  // Touch support
  var lastTouchDist = 0;
  canvas.addEventListener('touchstart', function (e) {
    if (e.touches.length === 2) {
      lastTouchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    }
  });
  canvas.addEventListener('touchmove', function (e) {
    if (e.touches.length === 2) {
      e.preventDefault();
      var dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      if (lastTouchDist > 0) {
        var delta = dist / lastTouchDist;
        scale *= delta;
        scale = Math.max(0.3, Math.min(3, scale));
      }
      lastTouchDist = dist;
    }
  }, { passive: false });

  // Reset zoom on double-click
  canvas.addEventListener('dblclick', function () {
    scale = 1; offsetX = 0; offsetY = 0;
  });

  // Export current transform for use by rendering code
  window.__evidenceGraphTransform = function () {
    return { scale: scale, offsetX: offsetX, offsetY: offsetY };
  };
})();

// ============ Disagreement Map Renderer ============

/**
 * Render a DisagreementMap onto the evidence graph canvas.
 * @param {Object} map - DisagreementMap JSON with ticker, conflict_points, etc.
 */
window.renderDisagreementMap = function (map) {
  if (!map || !map.conflict_points) return;

  var nodes = [];
  var edges = [];
  var centerX = 400, centerY = 300;

  // Central node: the ticker
  nodes.push({
    id: 'ticker',
    label: map.ticker || '???',
    type: 'ticker',
    x: centerX, y: centerY, fixed: true,
  });

  var conflicts = map.conflict_points.slice(0, 5);
  var radius = 200;
  conflicts.forEach(function (cp, i) {
    var angle = (2 * Math.PI * i) / conflicts.length - Math.PI / 2;
    var nx = centerX + radius * Math.cos(angle);
    var ny = centerY + radius * Math.sin(angle);

    // Conflict node
    var cid = 'conflict_' + i;
    nodes.push({
      id: cid,
      label: cp.claim ? cp.claim.slice(0, 40) : 'Conflict ' + (i + 1),
      type: 'conflict',
      x: nx, y: ny,
      details: cp,
    });
    edges.push({ from: 'ticker', to: cid, type: 'conflict' });

    // Bullish personas as sub-nodes
    (cp.bullish_personas || []).slice(0, 3).forEach(function (pid, j) {
      var bid = 'bull_' + i + '_' + j;
      nodes.push({
        id: bid,
        label: pid,
        type: 'bullish',
        x: nx + 60 + j * 20,
        y: ny - 20 + j * 15,
      });
      edges.push({ from: cid, to: bid, type: 'supports' });
    });

    // Bearish personas as sub-nodes
    (cp.bearish_personas || []).slice(0, 3).forEach(function (pid, j) {
      var bid = 'bear_' + i + '_' + j;
      nodes.push({
        id: bid,
        label: pid,
        type: 'bearish',
        x: nx - 60 - j * 20,
        y: ny + 20 - j * 15,
      });
      edges.push({ from: cid, to: bid, type: 'contradicts' });
    });
  });

  window.__evidenceGraphData = { nodes: nodes, edges: edges };
  if (window.__evidenceGraphRender) window.__evidenceGraphRender();
};
