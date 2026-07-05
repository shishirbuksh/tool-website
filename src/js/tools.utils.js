(function () {
  'use strict';

  window.sbr = window.sbr || {};

  /* ── Clipboard ── */
  window.sbr.copyToClipboard = function (text, btnEl, successMsg) {
    if (!text) return;
    var fallback = function () {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed'; ta.style.left = '-9999px'; ta.style.top = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        if (btnEl) {
          var orig = btnEl.innerHTML;
          btnEl.innerHTML = (successMsg || 'Copied!');
          btnEl.disabled = true;
          setTimeout(function () {
            btnEl.innerHTML = orig;
            btnEl.disabled = false;
          }, 2000);
        }
      } catch (e) {
        console.warn('[sbr] Clipboard fallback also failed:', e);
      }
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        if (!btnEl) return;
        var orig = btnEl.innerHTML;
        btnEl.innerHTML = (successMsg || 'Copied!');
        btnEl.disabled = true;
        setTimeout(function () {
          btnEl.innerHTML = orig;
          btnEl.disabled = false;
        }, 2000);
      })['catch'](function () {
        fallback();
      });
    } else {
      fallback();
    }
  };

  /* ── File size formatting ── */
  window.sbr.formatFileSize = function (bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  /* ── Download data URL ── */
  window.sbr.downloadDataUrl = function (filename, dataUrl) {
    var link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  /* ── Download canvas as image ── */
  window.sbr.downloadCanvas = function (canvasId, filename) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) {
      canvas = document.querySelector('#' + canvasId.replace('#', '') + ' canvas');
    }
    if (!canvas) return;
    window.sbr.downloadDataUrl(filename, canvas.toDataURL('image/png'));
  };

  /* ── Loader show/hide ── */
  window.sbr.showLoader = function (id) {
    var el = document.getElementById(id);
    if (el) {
      el.classList.remove('hidden');
      el.setAttribute('aria-hidden', 'false');
      document.body.setAttribute('aria-busy', 'true');
    }
  };
  window.sbr.hideLoader = function (id) {
    var el = document.getElementById(id);
    if (el) {
      el.classList.add('hidden');
      el.setAttribute('aria-hidden', 'true');
      document.body.removeAttribute('aria-busy');
    }
  };

  /* ── Sanitize HTML (basic XSS prevention) ── */
  window.sbr.sanitizeHtml = function (str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  };

  /* ── Format currency ── */
  window.sbr.formatCurrency = function (value, currency) {
    currency = currency || 'USD';
    try {
      return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency }).format(value);
    } catch (e) {
      return '$' + value.toFixed(2);
    }
  };

  /* ── Debounce ── */
  window.sbr.debounce = function (fn, ms) {
    var timer = null;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  };

  /* ── Global error handler ── */
  window.sbr.initErrorHandler = function () {
    window.onerror = function (msg, url, line, col, err) {
      console.error('[sbr] Uncaught error:', msg, 'at', url, line + ':' + col);
      return true;
    };
    window.addEventListener('unhandledrejection', function (e) {
      console.error('[sbr] Unhandled promise rejection:', e.reason);
    });
  };
  window.sbr.initErrorHandler();

  /* ── Delegate: copy-to-clipboard buttons ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-copy-target]');
    if (btn) {
      var targetId = btn.getAttribute('data-copy-target');
      var targetEl = document.getElementById(targetId);
      if (targetEl) {
        var text = targetEl.textContent;
        window.sbr.copyToClipboard(text, btn);
      }
    }
  });

  /* ── Lucide icon renderer (for JS templates) ── */
  var __lucideIcons = {
    "check": '<path d="M20 6 9 17l-5-5" />',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />',
    "check-circle-2": '<circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" />',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z" /><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12" /><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17" />',
    "boxes": '<path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z" /><path d="m7 16.5-4.74-2.85" /><path d="m7 16.5 5-3" /><path d="M7 16.5v5.17" /><path d="M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z" /><path d="m17 16.5-5-3" /><path d="m17 16.5 4.74-2.85" /><path d="M17 16.5v5.17" /><path d="M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z" /><path d="M12 8 7.26 5.15" /><path d="m12 8 4.74-2.85" /><path d="M12 13.5V8" />',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />',
    "scroll": '<path d="M19 17V5a2 2 0 0 0-2-2H4" /><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3" />',
    "git-merge": '<circle cx="18" cy="18" r="3" /><circle cx="6" cy="6" r="3" /><path d="M6 21V9a9 9 0 0 0 9 9" />',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />'
  };
  window.__lucide = function (name, size) {
    size = size || 24;
    var inner = __lucideIcons[name];
    if (!inner) return '';
    return '<svg class="lucide lucide-' + name + '" xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + inner + '</svg>';
  };

  /* ── Delegate: loading buttons ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-loading]');
    if (btn && btn.getAttribute('data-loading')) {
      btn.innerHTML = 'Processing...';
      btn.disabled = true;
    }
  });
})();
