/* diagram-zoom.js — click-to-expand + pan/zoom for inline diagrams.
   Vanilla, no dependencies. Works on rendered mermaid SVG, hand-written <svg>, and <img>.
   Call DiagramZoom.init() after the diagrams exist in the DOM (i.e. after mermaid.run()). */
(function (global) {
  'use strict';

  var MIN_SCALE = 0.1;
  var MAX_SCALE = 16;
  var STEP = 1.3;
  var PAD = 32;       /* px of breathing room when fitting */
  var READABLE = 0.75; /* below this, fit-to-screen text is too small to read */

  var overlay, stage, canvas, title, level;
  var current = null;      /* { node, w, h } */
  var scale = 1, fitScale = 1, tx = 0, ty = 0;
  var pointers = new Map();
  var pinch = null;        /* { dist, cx, cy } */
  var lastFocus = null;

  /* ---------- overlay ---------- */

  function buildOverlay() {
    overlay = document.createElement('div');
    overlay.className = 'dz-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Expanded diagram');
    overlay.hidden = true;
    overlay.innerHTML =
      '<div class="dz-bar">' +
        '<p class="dz-title"></p>' +
        '<div class="dz-controls">' +
          '<button type="button" class="dz-btn" data-dz="out" aria-label="Zoom out">−</button>' +
          '<span class="dz-level" role="status" aria-live="polite">100%</span>' +
          '<button type="button" class="dz-btn" data-dz="in" aria-label="Zoom in">+</button>' +
          '<button type="button" class="dz-btn" data-dz="fit" aria-label="Fit whole diagram on screen">Fit</button>' +
          '<button type="button" class="dz-btn dz-close" data-dz="close" aria-label="Close expanded diagram">✕</button>' +
        '</div>' +
      '</div>' +
      '<div class="dz-stage"><div class="dz-canvas"></div></div>' +
      '<p class="dz-hint">Scroll or pinch to zoom · drag to pan · double-click to fit · Esc to close</p>';

    document.body.appendChild(overlay);
    stage = overlay.querySelector('.dz-stage');
    canvas = overlay.querySelector('.dz-canvas');
    title = overlay.querySelector('.dz-title');
    level = overlay.querySelector('.dz-level');

    overlay.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-dz]');
      if (btn) {
        var a = btn.getAttribute('data-dz');
        if (a === 'close') close();
        else if (a === 'fit') fit();
        else zoomBy(a === 'in' ? STEP : 1 / STEP);
        return;
      }
      if (e.target === stage || e.target === overlay) close();
    });

    stage.addEventListener('wheel', onWheel, { passive: false });
    stage.addEventListener('pointerdown', onPointerDown);
    stage.addEventListener('pointermove', onPointerMove);
    stage.addEventListener('pointerup', onPointerUp);
    stage.addEventListener('pointercancel', onPointerUp);
    stage.addEventListener('dblclick', function (e) { e.preventDefault(); fit(); });
    /* Capture phase + stopImmediatePropagation: while the overlay is open it owns the arrow
       keys and Esc, so a host page's own key handling (slide nav, shortcuts) stays quiet. */
    document.addEventListener('keydown', onKeyDown, true);
    global.addEventListener('resize', function () { if (!overlay.hidden) openView(); });
  }

  /* ---------- measuring ---------- */

  function naturalSize(node) {
    var w = 0, h = 0;
    if (node.tagName.toLowerCase() === 'svg') {
      var vb = node.viewBox && node.viewBox.baseVal;
      if (vb && vb.width && vb.height) { w = vb.width; h = vb.height; }
      if (!w) {
        var r = node.getBoundingClientRect();
        w = r.width; h = r.height;
      }
    } else if (node.tagName.toLowerCase() === 'img') {
      w = node.naturalWidth || node.getBoundingClientRect().width;
      h = node.naturalHeight || node.getBoundingClientRect().height;
    } else {
      var rect = node.getBoundingClientRect();
      w = rect.width; h = rect.height;
    }
    return { w: Math.max(w, 1), h: Math.max(h, 1) };
  }

  /* ---------- transform ---------- */

  function apply() {
    canvas.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
    level.textContent = Math.round(scale * 100) + '%';   /* 100% = 1:1 with the diagram's own units */
  }

  function clamp(s) { return Math.min(MAX_SCALE, Math.max(MIN_SCALE, s)); }

  /* Scale that shows the whole diagram inside the stage. */
  function computeFit() {
    var r = stage.getBoundingClientRect();
    var s = Math.min((r.width - PAD * 2) / current.w, (r.height - PAD * 2) / current.h);
    return (isFinite(s) && s > 0) ? s : 1;
  }

  function fit() {
    if (!current) return;
    fitScale = computeFit();
    scale = fitScale;
    tx = 0; ty = 0;
    apply();
  }

  /* Opening view: show the whole diagram when that stays readable; otherwise open at a
     legible scale (never below fit, never above 1:1) and let the user pan. This is what
     makes a wide flowchart usable on a phone, where fit-to-screen is unreadably small. */
  function openView() {
    if (!current) return;
    fitScale = computeFit();
    scale = fitScale >= READABLE ? fitScale : Math.min(1, Math.max(fitScale, cover()));
    tx = 0; ty = 0;
    apply();
  }

  function cover() {
    var r = stage.getBoundingClientRect();
    return Math.max((r.width - PAD * 2) / current.w, (r.height - PAD * 2) / current.h);
  }

  /* zoom keeping the point (px, py) — stage-relative — anchored */
  function zoomAt(factor, px, py) {
    var r = stage.getBoundingClientRect();
    var cx = px - r.width / 2;
    var cy = py - r.height / 2;
    var next = clamp(scale * factor);
    var k = next / scale;
    tx = cx - (cx - tx) * k;
    ty = cy - (cy - ty) * k;
    scale = next;
    apply();
  }

  function zoomBy(factor) {
    var r = stage.getBoundingClientRect();
    zoomAt(factor, r.width / 2, r.height / 2);
  }

  /* ---------- input ---------- */

  function onWheel(e) {
    if (overlay.hidden) return;
    e.preventDefault();
    var r = stage.getBoundingClientRect();
    var factor = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0025));
    zoomAt(factor, e.clientX - r.left, e.clientY - r.top);
  }

  function onPointerDown(e) {
    if (e.target.closest('[data-dz]')) return;
    stage.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) pinch = pinchState();
    stage.classList.add('is-grabbing');
  }

  function pinchState() {
    var pts = Array.from(pointers.values());
    var dx = pts[0].x - pts[1].x, dy = pts[0].y - pts[1].y;
    return {
      dist: Math.hypot(dx, dy) || 1,
      cx: (pts[0].x + pts[1].x) / 2,
      cy: (pts[0].y + pts[1].y) / 2
    };
  }

  function onPointerMove(e) {
    var prev = pointers.get(e.pointerId);
    if (!prev) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.size >= 2) {
      var now = pinchState();
      if (pinch) {
        var r = stage.getBoundingClientRect();
        tx += now.cx - pinch.cx;
        ty += now.cy - pinch.cy;
        apply();
        zoomAt(now.dist / pinch.dist, now.cx - r.left, now.cy - r.top);
      }
      pinch = now;
      return;
    }
    tx += e.clientX - prev.x;
    ty += e.clientY - prev.y;
    apply();
  }

  function onPointerUp(e) {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) stage.classList.remove('is-grabbing');
  }

  function onKeyDown(e) {
    if (overlay.hidden) return;
    var k = e.key;
    if (k === 'Tab') { trapFocus(e); return; }
    if (k === 'Escape') close();
    else if (k === '+' || k === '=') zoomBy(STEP);
    else if (k === '-' || k === '_') zoomBy(1 / STEP);
    else if (k === '0') fit();
    else if (k === 'ArrowLeft') { tx += 60; apply(); }
    else if (k === 'ArrowRight') { tx -= 60; apply(); }
    else if (k === 'ArrowUp') { ty += 60; apply(); }
    else if (k === 'ArrowDown') { ty -= 60; apply(); }
    else if (k === ' ' || k === 'PageUp' || k === 'PageDown') { /* swallow: host page nav */ }
    else return;
    e.preventDefault();
    e.stopImmediatePropagation();
  }

  function trapFocus(e) {
    var items = overlay.querySelectorAll('button');
    var first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  /* ---------- open / close ---------- */

  function open(source, label) {
    if (!overlay) buildOverlay();
    var node = source.cloneNode(true);
    node.classList.remove('dz-target');
    var size = naturalSize(source);

    /* Mermaid scopes its generated CSS by the SVG's own id (#mermaid-N .node rect { … }).
       Re-id the clone and rewrite that id inside its <style> blocks, or the copy renders unstyled. */
    var srcId = source.getAttribute('id');
    if (srcId) {
      var newId = 'dz-clone-' + srcId;
      node.setAttribute('id', newId);
      node.querySelectorAll('style').forEach(function (st) {
        st.textContent = st.textContent.split('#' + srcId).join('#' + newId);
      });
    }

    if (node.tagName.toLowerCase() === 'svg') {
      node.removeAttribute('style');
      node.setAttribute('width', size.w);
      node.setAttribute('height', size.h);
      node.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    } else {
      node.style.width = size.w + 'px';
      node.style.height = 'auto';
    }

    canvas.replaceChildren(node);
    canvas.style.width = size.w + 'px';
    canvas.style.height = size.h + 'px';
    canvas.style.marginLeft = (-size.w / 2) + 'px';
    canvas.style.marginTop = (-size.h / 2) + 'px';
    current = { node: node, w: size.w, h: size.h };

    title.textContent = label || '';
    lastFocus = document.activeElement;
    overlay.hidden = false;
    document.documentElement.classList.add('dz-open');
    openView();
    overlay.querySelector('.dz-close').focus();
  }

  function close() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    canvas.replaceChildren();
    current = null;
    pointers.clear();
    pinch = null;
    document.documentElement.classList.remove('dz-open');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* ---------- wiring ---------- */

  function wrap(target) {
    var host = target.parentElement;
    if (!host) return;
    if (host.classList.contains('dz-figure')) return;

    /* Reuse an existing wrapper (<figure>, pre.mermaid, .diagram); otherwise make one. */
    var reusable = host.tagName === 'FIGURE' ||
                   host.classList.contains('mermaid') ||
                   host.classList.contains('diagram');
    if (!reusable) {
      var fig = document.createElement('figure');
      fig.className = 'dz-figure';
      host.insertBefore(fig, target);
      fig.appendChild(target);
      host = fig;
    }
    host.classList.add('dz-figure');

    var cap = host.querySelector('figcaption');
    if (!cap && host.nextElementSibling && host.nextElementSibling.tagName === 'FIGCAPTION') {
      cap = host.nextElementSibling;
    }
    var label = ((cap && cap.textContent) || target.getAttribute('aria-label') || '').trim();

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'dz-expand';
    btn.setAttribute('aria-label', label ? 'Expand diagram: ' + label : 'Expand diagram');
    btn.innerHTML = '<span aria-hidden="true">\u2921</span><span class="dz-expand-text">Expand</span>';
    host.appendChild(btn);

    host.addEventListener('click', function (e) {
      if (e.target.closest('a')) return;
      e.preventDefault();
      open(target, label);
    });
    target.classList.add('dz-target');
    if (!target.hasAttribute('role')) target.setAttribute('role', 'img');
  }

  function init(opts) {
    opts = opts || {};
    var selector = opts.selector || '.mermaid > svg, .diagram > svg, figure > svg, [data-zoomable]';
    if (!overlay) buildOverlay();
    document.querySelectorAll(selector).forEach(function (el) {
      if (el.closest('.dz-overlay')) return;
      wrap(el);
    });
  }

  global.DiagramZoom = { init: init, open: open, close: close };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { if (!global.DIAGRAM_ZOOM_MANUAL) init(); });
  } else if (!global.DIAGRAM_ZOOM_MANUAL) {
    init();
  }
})(window);
