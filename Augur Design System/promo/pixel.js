/* ============================================================
   Augur promo — pixel sprite engine (original genre art)
   Renders crisp pixel sprites via a single box-shadow stack.
   Usage: mountSprite(el, 'slime', 7)
   ============================================================ */
(function () {
  // palettes
  const P = {
    slime: { k:'#0a1626', D:'#5cc8ff', s:'#2a7fb8', w:'#e8f7ff', e:'#0a1626', m:'#16527e' },
    chest: { k:'#1c1208', w:'#8a5a2b', W:'#b9813f', g:'#a9842a', G:'#f0d573', d:'#5e3c18' },
    coin:  { k:'#7c5e18', g:'#d4af37', G:'#f8e58a' },
    sword: { k:'#0a0a12', b:'#cfd6e6', w:'#ffffff', g:'#d4af37', G:'#f0d573', h:'#5e3c18' },
    heart: { k:'#3a0a14', r:'#ff3b5c', w:'#ffd0da' },
  };

  // sprite maps (rows of chars; '.' = transparent)
  const M = {
    slime: [
      '......kkkk......',
      '....kkDDDDkk....',
      '...kDDDDDDDDk...',
      '..kDwDDDDDDDDk..',
      '.kDDDDDDDDDDDDk.',
      '.kDDeeDDDDeeDDk.',
      '.kDDeeDDDDeeDDk.',
      '.kDDDDDDDDDDDDk.',
      '.kDDDDmmmmDDDDk.',
      '.kDsDDDDDDDDsDk.',
      '.kkDDDDDDDDDDkk.',
      '..kkkkkkkkkkkk..',
    ],
    chest: [
      '..gggggggggg..',
      '.gGGGGGGGGGGg.',
      'gGWwwwwwwwwWGg',
      'gGWwwwwwwwwWGg',
      'kkkkkggkkkkkkk',
      'gWwwwwGGwwwwWg',
      'gWwwwwGGwwwwWg',
      'gWwwwwwwwwwwWg',
      'gWwwwwwwwwwwWg',
      'gkkkkkkkkkkkkg',
      '.gggggggggggg.',
    ],
    coin: [
      '..ggGGgg..',
      '.gGGGGGGg.',
      'gGGkggkGGg',
      'gGkggggkGg',
      'gGkggggkGg',
      'gGGkggkGGg',
      '.gGGGGGGg.',
      '..ggGGgg..',
    ],
    sword: [
      '.......kg',
      '......kGk',
      '.....kbGk',
      '....kbbk.',
      '...kbbk..',
      '..kbbk...',
      '.kbbk.kk.',
      'kgggkkhk.',
      '.kgggkk..',
      '...khk...',
      '...khk...',
      '...kk....',
    ],
    heart: [
      '.kk..kk.',
      'krrkkrrk',
      'krwrrrrk',
      'krrrrrrk',
      '.krrrrk.',
      '..krrk..',
      '...kk...',
    ],
  };

  function shadowFor(name, px) {
    const map = M[name], pal = P[name];
    const out = [];
    for (let y = 0; y < map.length; y++) {
      const row = map[y];
      for (let x = 0; x < row.length; x++) {
        const c = pal[row[x]];
        if (c) out.push(`${x * px}px ${y * px}px 0 0 ${c}`);
      }
    }
    const w = Math.max(...map.map(r => r.length));
    return { shadow: out.join(','), w: w * px, h: map.length * px };
  }

  window.mountSprite = function (el, name, px = 7) {
    if (!el || !M[name]) return;
    const { shadow, w, h } = shadowFor(name, px);
    el.style.position = 'relative';
    el.style.width = w + 'px';
    el.style.height = h + 'px';
    const dot = document.createElement('div');
    dot.style.cssText =
      `position:absolute;top:0;left:0;width:${px}px;height:${px}px;background:transparent;box-shadow:${shadow};`;
    el.appendChild(dot);
  };

  // auto-mount any [data-sprite]
  window.mountAllSprites = function () {
    document.querySelectorAll('[data-sprite]').forEach(el => {
      if (el.dataset.mounted) return;
      mountSprite(el, el.dataset.sprite, parseInt(el.dataset.px || '7', 10));
      el.dataset.mounted = '1';
    });
  };
  document.addEventListener('DOMContentLoaded', window.mountAllSprites);
})();
