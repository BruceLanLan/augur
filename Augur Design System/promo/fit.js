/* Scale a 1600×900 .frame to fit the capture viewport, so the full
   composition is captured (and body shrinks to the scaled size — no letterbox). */
(function () {
  function fit() {
    var f = document.querySelector('.frame');
    if (!f) return;
    var s = window.innerWidth / 1600;
    if (s > 1) s = 1;
    f.style.transformOrigin = 'top left';
    f.style.transform = 'scale(' + s + ')';
    document.body.style.margin = '0';
    document.body.style.overflow = 'hidden';
    document.body.style.width = (1600 * s) + 'px';
    document.body.style.height = (900 * s) + 'px';
    document.documentElement.style.background = '#0a0a0f';
  }
  window.augFit = fit;
  window.addEventListener('resize', fit);
  document.addEventListener('DOMContentLoaded', function () { fit(); if (window.mountAllSprites) window.mountAllSprites(); });
  setTimeout(fit, 60);
})();
