(() => {
  // src/js/tools.utils.js
  (function() {
    "use strict";
    window.sbr = window.sbr || {};
    window.sbr.copyToClipboard = function(text, btnEl, successMsg) {
      if (!text) return;
      var fallback = function() {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        ta.style.top = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand("copy");
          if (btnEl) {
            var orig = btnEl.innerHTML;
            btnEl.innerHTML = successMsg || "Copied!";
            btnEl.disabled = true;
            setTimeout(function() {
              btnEl.innerHTML = orig;
              btnEl.disabled = false;
            }, 2e3);
          }
        } catch (e) {
          console.warn("[sbr] Clipboard fallback also failed:", e);
        }
        document.body.removeChild(ta);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function() {
          if (!btnEl) return;
          var orig = btnEl.innerHTML;
          btnEl.innerHTML = successMsg || "Copied!";
          btnEl.disabled = true;
          setTimeout(function() {
            btnEl.innerHTML = orig;
            btnEl.disabled = false;
          }, 2e3);
        })["catch"](function() {
          fallback();
        });
      } else {
        fallback();
      }
    };
    window.sbr.formatFileSize = function(bytes) {
      if (bytes < 1024) return bytes + " B";
      if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
      return (bytes / 1048576).toFixed(2) + " MB";
    };
    window.sbr.downloadDataUrl = function(filename, dataUrl) {
      var link = document.createElement("a");
      link.download = filename;
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };
    window.sbr.downloadCanvas = function(canvasId, filename) {
      var canvas = document.getElementById(canvasId);
      if (!canvas) {
        canvas = document.querySelector("#" + canvasId.replace("#", "") + " canvas");
      }
      if (!canvas) return;
      window.sbr.downloadDataUrl(filename, canvas.toDataURL("image/png"));
    };
    window.sbr.showLoader = function(id) {
      var el = document.getElementById(id);
      if (el) {
        el.classList.remove("hidden");
        el.setAttribute("aria-hidden", "false");
        document.body.setAttribute("aria-busy", "true");
      }
    };
    window.sbr.hideLoader = function(id) {
      var el = document.getElementById(id);
      if (el) {
        el.classList.add("hidden");
        el.setAttribute("aria-hidden", "true");
        document.body.removeAttribute("aria-busy");
      }
    };
    window.sbr.sanitizeHtml = function(str) {
      var d = document.createElement("div");
      d.textContent = str;
      return d.innerHTML;
    };
    window.sbr.formatCurrency = function(value, currency) {
      currency = currency || "USD";
      try {
        return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
      } catch (e) {
        return "$" + value.toFixed(2);
      }
    };
    window.sbr.debounce = function(fn, ms) {
      var timer = null;
      return function() {
        var ctx = this, args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function() {
          fn.apply(ctx, args);
        }, ms);
      };
    };
    window.sbr.initErrorHandler = function() {
      window.onerror = function(msg, url, line, col, err) {
        console.error("[sbr] Uncaught error:", msg, "at", url, line + ":" + col);
        return true;
      };
      window.addEventListener("unhandledrejection", function(e) {
        console.error("[sbr] Unhandled promise rejection:", e.reason);
      });
    };
    window.sbr.initErrorHandler();
    document.addEventListener("click", function(e) {
      var btn = e.target.closest("[data-copy-target]");
      if (btn) {
        var targetId = btn.getAttribute("data-copy-target");
        var targetEl = document.getElementById(targetId);
        if (targetEl) {
          var text = targetEl.textContent;
          window.sbr.copyToClipboard(text, btn);
        }
      }
    });
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
    window.__lucide = function(name, size) {
      size = size || 24;
      var inner = __lucideIcons[name];
      if (!inner) return "";
      return '<svg class="lucide lucide-' + name + '" xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + inner + "</svg>";
    };
    document.addEventListener("click", function(e) {
      var btn = e.target.closest("[data-loading]");
      if (btn && btn.getAttribute("data-loading")) {
        btn.innerHTML = "Processing...";
        btn.disabled = true;
      }
    });
  })();
})();
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vLi4vc3JjL2pzL3Rvb2xzLnV0aWxzLmpzIl0sCiAgInNvdXJjZXNDb250ZW50IjogWyIoZnVuY3Rpb24gKCkge1xuICAndXNlIHN0cmljdCc7XG5cbiAgd2luZG93LnNiciA9IHdpbmRvdy5zYnIgfHwge307XG5cbiAgLyogXHUyNTAwXHUyNTAwIENsaXBib2FyZCBcdTI1MDBcdTI1MDAgKi9cbiAgd2luZG93LnNici5jb3B5VG9DbGlwYm9hcmQgPSBmdW5jdGlvbiAodGV4dCwgYnRuRWwsIHN1Y2Nlc3NNc2cpIHtcbiAgICBpZiAoIXRleHQpIHJldHVybjtcbiAgICB2YXIgZmFsbGJhY2sgPSBmdW5jdGlvbiAoKSB7XG4gICAgICB2YXIgdGEgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCd0ZXh0YXJlYScpO1xuICAgICAgdGEudmFsdWUgPSB0ZXh0O1xuICAgICAgdGEuc3R5bGUucG9zaXRpb24gPSAnZml4ZWQnOyB0YS5zdHlsZS5sZWZ0ID0gJy05OTk5cHgnOyB0YS5zdHlsZS50b3AgPSAnLTk5OTlweCc7XG4gICAgICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKHRhKTtcbiAgICAgIHRhLnNlbGVjdCgpO1xuICAgICAgdHJ5IHtcbiAgICAgICAgZG9jdW1lbnQuZXhlY0NvbW1hbmQoJ2NvcHknKTtcbiAgICAgICAgaWYgKGJ0bkVsKSB7XG4gICAgICAgICAgdmFyIG9yaWcgPSBidG5FbC5pbm5lckhUTUw7XG4gICAgICAgICAgYnRuRWwuaW5uZXJIVE1MID0gKHN1Y2Nlc3NNc2cgfHwgJ0NvcGllZCEnKTtcbiAgICAgICAgICBidG5FbC5kaXNhYmxlZCA9IHRydWU7XG4gICAgICAgICAgc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgICAgICAgICBidG5FbC5pbm5lckhUTUwgPSBvcmlnO1xuICAgICAgICAgICAgYnRuRWwuZGlzYWJsZWQgPSBmYWxzZTtcbiAgICAgICAgICB9LCAyMDAwKTtcbiAgICAgICAgfVxuICAgICAgfSBjYXRjaCAoZSkge1xuICAgICAgICBjb25zb2xlLndhcm4oJ1tzYnJdIENsaXBib2FyZCBmYWxsYmFjayBhbHNvIGZhaWxlZDonLCBlKTtcbiAgICAgIH1cbiAgICAgIGRvY3VtZW50LmJvZHkucmVtb3ZlQ2hpbGQodGEpO1xuICAgIH07XG4gICAgaWYgKG5hdmlnYXRvci5jbGlwYm9hcmQgJiYgbmF2aWdhdG9yLmNsaXBib2FyZC53cml0ZVRleHQpIHtcbiAgICAgIG5hdmlnYXRvci5jbGlwYm9hcmQud3JpdGVUZXh0KHRleHQpLnRoZW4oZnVuY3Rpb24gKCkge1xuICAgICAgICBpZiAoIWJ0bkVsKSByZXR1cm47XG4gICAgICAgIHZhciBvcmlnID0gYnRuRWwuaW5uZXJIVE1MO1xuICAgICAgICBidG5FbC5pbm5lckhUTUwgPSAoc3VjY2Vzc01zZyB8fCAnQ29waWVkIScpO1xuICAgICAgICBidG5FbC5kaXNhYmxlZCA9IHRydWU7XG4gICAgICAgIHNldFRpbWVvdXQoZnVuY3Rpb24gKCkge1xuICAgICAgICAgIGJ0bkVsLmlubmVySFRNTCA9IG9yaWc7XG4gICAgICAgICAgYnRuRWwuZGlzYWJsZWQgPSBmYWxzZTtcbiAgICAgICAgfSwgMjAwMCk7XG4gICAgICB9KVsnY2F0Y2gnXShmdW5jdGlvbiAoKSB7XG4gICAgICAgIGZhbGxiYWNrKCk7XG4gICAgICB9KTtcbiAgICB9IGVsc2Uge1xuICAgICAgZmFsbGJhY2soKTtcbiAgICB9XG4gIH07XG5cbiAgLyogXHUyNTAwXHUyNTAwIEZpbGUgc2l6ZSBmb3JtYXR0aW5nIFx1MjUwMFx1MjUwMCAqL1xuICB3aW5kb3cuc2JyLmZvcm1hdEZpbGVTaXplID0gZnVuY3Rpb24gKGJ5dGVzKSB7XG4gICAgaWYgKGJ5dGVzIDwgMTAyNCkgcmV0dXJuIGJ5dGVzICsgJyBCJztcbiAgICBpZiAoYnl0ZXMgPCAxMDQ4NTc2KSByZXR1cm4gKGJ5dGVzIC8gMTAyNCkudG9GaXhlZCgxKSArICcgS0InO1xuICAgIHJldHVybiAoYnl0ZXMgLyAxMDQ4NTc2KS50b0ZpeGVkKDIpICsgJyBNQic7XG4gIH07XG5cbiAgLyogXHUyNTAwXHUyNTAwIERvd25sb2FkIGRhdGEgVVJMIFx1MjUwMFx1MjUwMCAqL1xuICB3aW5kb3cuc2JyLmRvd25sb2FkRGF0YVVybCA9IGZ1bmN0aW9uIChmaWxlbmFtZSwgZGF0YVVybCkge1xuICAgIHZhciBsaW5rID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnYScpO1xuICAgIGxpbmsuZG93bmxvYWQgPSBmaWxlbmFtZTtcbiAgICBsaW5rLmhyZWYgPSBkYXRhVXJsO1xuICAgIGRvY3VtZW50LmJvZHkuYXBwZW5kQ2hpbGQobGluayk7XG4gICAgbGluay5jbGljaygpO1xuICAgIGRvY3VtZW50LmJvZHkucmVtb3ZlQ2hpbGQobGluayk7XG4gIH07XG5cbiAgLyogXHUyNTAwXHUyNTAwIERvd25sb2FkIGNhbnZhcyBhcyBpbWFnZSBcdTI1MDBcdTI1MDAgKi9cbiAgd2luZG93LnNici5kb3dubG9hZENhbnZhcyA9IGZ1bmN0aW9uIChjYW52YXNJZCwgZmlsZW5hbWUpIHtcbiAgICB2YXIgY2FudmFzID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoY2FudmFzSWQpO1xuICAgIGlmICghY2FudmFzKSB7XG4gICAgICBjYW52YXMgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yKCcjJyArIGNhbnZhc0lkLnJlcGxhY2UoJyMnLCAnJykgKyAnIGNhbnZhcycpO1xuICAgIH1cbiAgICBpZiAoIWNhbnZhcykgcmV0dXJuO1xuICAgIHdpbmRvdy5zYnIuZG93bmxvYWREYXRhVXJsKGZpbGVuYW1lLCBjYW52YXMudG9EYXRhVVJMKCdpbWFnZS9wbmcnKSk7XG4gIH07XG5cbiAgLyogXHUyNTAwXHUyNTAwIExvYWRlciBzaG93L2hpZGUgXHUyNTAwXHUyNTAwICovXG4gIHdpbmRvdy5zYnIuc2hvd0xvYWRlciA9IGZ1bmN0aW9uIChpZCkge1xuICAgIHZhciBlbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKGlkKTtcbiAgICBpZiAoZWwpIHtcbiAgICAgIGVsLmNsYXNzTGlzdC5yZW1vdmUoJ2hpZGRlbicpO1xuICAgICAgZWwuc2V0QXR0cmlidXRlKCdhcmlhLWhpZGRlbicsICdmYWxzZScpO1xuICAgICAgZG9jdW1lbnQuYm9keS5zZXRBdHRyaWJ1dGUoJ2FyaWEtYnVzeScsICd0cnVlJyk7XG4gICAgfVxuICB9O1xuICB3aW5kb3cuc2JyLmhpZGVMb2FkZXIgPSBmdW5jdGlvbiAoaWQpIHtcbiAgICB2YXIgZWwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCk7XG4gICAgaWYgKGVsKSB7XG4gICAgICBlbC5jbGFzc0xpc3QuYWRkKCdoaWRkZW4nKTtcbiAgICAgIGVsLnNldEF0dHJpYnV0ZSgnYXJpYS1oaWRkZW4nLCAndHJ1ZScpO1xuICAgICAgZG9jdW1lbnQuYm9keS5yZW1vdmVBdHRyaWJ1dGUoJ2FyaWEtYnVzeScpO1xuICAgIH1cbiAgfTtcblxuICAvKiBcdTI1MDBcdTI1MDAgU2FuaXRpemUgSFRNTCAoYmFzaWMgWFNTIHByZXZlbnRpb24pIFx1MjUwMFx1MjUwMCAqL1xuICB3aW5kb3cuc2JyLnNhbml0aXplSHRtbCA9IGZ1bmN0aW9uIChzdHIpIHtcbiAgICB2YXIgZCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ2RpdicpO1xuICAgIGQudGV4dENvbnRlbnQgPSBzdHI7XG4gICAgcmV0dXJuIGQuaW5uZXJIVE1MO1xuICB9O1xuXG4gIC8qIFx1MjUwMFx1MjUwMCBGb3JtYXQgY3VycmVuY3kgXHUyNTAwXHUyNTAwICovXG4gIHdpbmRvdy5zYnIuZm9ybWF0Q3VycmVuY3kgPSBmdW5jdGlvbiAodmFsdWUsIGN1cnJlbmN5KSB7XG4gICAgY3VycmVuY3kgPSBjdXJyZW5jeSB8fCAnVVNEJztcbiAgICB0cnkge1xuICAgICAgcmV0dXJuIG5ldyBJbnRsLk51bWJlckZvcm1hdCgnZW4tVVMnLCB7IHN0eWxlOiAnY3VycmVuY3knLCBjdXJyZW5jeTogY3VycmVuY3kgfSkuZm9ybWF0KHZhbHVlKTtcbiAgICB9IGNhdGNoIChlKSB7XG4gICAgICByZXR1cm4gJyQnICsgdmFsdWUudG9GaXhlZCgyKTtcbiAgICB9XG4gIH07XG5cbiAgLyogXHUyNTAwXHUyNTAwIERlYm91bmNlIFx1MjUwMFx1MjUwMCAqL1xuICB3aW5kb3cuc2JyLmRlYm91bmNlID0gZnVuY3Rpb24gKGZuLCBtcykge1xuICAgIHZhciB0aW1lciA9IG51bGw7XG4gICAgcmV0dXJuIGZ1bmN0aW9uICgpIHtcbiAgICAgIHZhciBjdHggPSB0aGlzLCBhcmdzID0gYXJndW1lbnRzO1xuICAgICAgY2xlYXJUaW1lb3V0KHRpbWVyKTtcbiAgICAgIHRpbWVyID0gc2V0VGltZW91dChmdW5jdGlvbiAoKSB7IGZuLmFwcGx5KGN0eCwgYXJncyk7IH0sIG1zKTtcbiAgICB9O1xuICB9O1xuXG4gIC8qIFx1MjUwMFx1MjUwMCBHbG9iYWwgZXJyb3IgaGFuZGxlciBcdTI1MDBcdTI1MDAgKi9cbiAgd2luZG93LnNici5pbml0RXJyb3JIYW5kbGVyID0gZnVuY3Rpb24gKCkge1xuICAgIHdpbmRvdy5vbmVycm9yID0gZnVuY3Rpb24gKG1zZywgdXJsLCBsaW5lLCBjb2wsIGVycikge1xuICAgICAgY29uc29sZS5lcnJvcignW3Nicl0gVW5jYXVnaHQgZXJyb3I6JywgbXNnLCAnYXQnLCB1cmwsIGxpbmUgKyAnOicgKyBjb2wpO1xuICAgICAgcmV0dXJuIHRydWU7XG4gICAgfTtcbiAgICB3aW5kb3cuYWRkRXZlbnRMaXN0ZW5lcigndW5oYW5kbGVkcmVqZWN0aW9uJywgZnVuY3Rpb24gKGUpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ1tzYnJdIFVuaGFuZGxlZCBwcm9taXNlIHJlamVjdGlvbjonLCBlLnJlYXNvbik7XG4gICAgfSk7XG4gIH07XG4gIHdpbmRvdy5zYnIuaW5pdEVycm9ySGFuZGxlcigpO1xuXG4gIC8qIFx1MjUwMFx1MjUwMCBEZWxlZ2F0ZTogY29weS10by1jbGlwYm9hcmQgYnV0dG9ucyBcdTI1MDBcdTI1MDAgKi9cbiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLCBmdW5jdGlvbiAoZSkge1xuICAgIHZhciBidG4gPSBlLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1jb3B5LXRhcmdldF0nKTtcbiAgICBpZiAoYnRuKSB7XG4gICAgICB2YXIgdGFyZ2V0SWQgPSBidG4uZ2V0QXR0cmlidXRlKCdkYXRhLWNvcHktdGFyZ2V0Jyk7XG4gICAgICB2YXIgdGFyZ2V0RWwgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCh0YXJnZXRJZCk7XG4gICAgICBpZiAodGFyZ2V0RWwpIHtcbiAgICAgICAgdmFyIHRleHQgPSB0YXJnZXRFbC50ZXh0Q29udGVudDtcbiAgICAgICAgd2luZG93LnNici5jb3B5VG9DbGlwYm9hcmQodGV4dCwgYnRuKTtcbiAgICAgIH1cbiAgICB9XG4gIH0pO1xuXG4gIC8qIFx1MjUwMFx1MjUwMCBMdWNpZGUgaWNvbiByZW5kZXJlciAoZm9yIEpTIHRlbXBsYXRlcykgXHUyNTAwXHUyNTAwICovXG4gIHZhciBfX2x1Y2lkZUljb25zID0ge1xuICAgIFwiY2hlY2tcIjogJzxwYXRoIGQ9XCJNMjAgNiA5IDE3bC01LTVcIiAvPicsXG4gICAgXCJjb3B5XCI6ICc8cmVjdCB3aWR0aD1cIjE0XCIgaGVpZ2h0PVwiMTRcIiB4PVwiOFwiIHk9XCI4XCIgcng9XCIyXCIgcnk9XCIyXCIgLz48cGF0aCBkPVwiTTQgMTZjLTEuMSAwLTItLjktMi0yVjRjMC0xLjEuOS0yIDItMmgxMGMxLjEgMCAyIC45IDIgMlwiIC8+JyxcbiAgICBcImNoZWNrLWNpcmNsZS0yXCI6ICc8Y2lyY2xlIGN4PVwiMTJcIiBjeT1cIjEyXCIgcj1cIjEwXCIgLz48cGF0aCBkPVwibTkgMTIgMiAyIDQtNFwiIC8+JyxcbiAgICBcImxheWVyc1wiOiAnPHBhdGggZD1cIk0xMi44MyAyLjE4YTIgMiAwIDAgMC0xLjY2IDBMMi42IDYuMDhhMSAxIDAgMCAwIDAgMS44M2w4LjU4IDMuOTFhMiAyIDAgMCAwIDEuNjYgMGw4LjU4LTMuOWExIDEgMCAwIDAgMC0xLjgzelwiIC8+PHBhdGggZD1cIk0yIDEyYTEgMSAwIDAgMCAuNTguOTFsOC42IDMuOTFhMiAyIDAgMCAwIDEuNjUgMGw4LjU4LTMuOUExIDEgMCAwIDAgMjIgMTJcIiAvPjxwYXRoIGQ9XCJNMiAxN2ExIDEgMCAwIDAgLjU4LjkxbDguNiAzLjkxYTIgMiAwIDAgMCAxLjY1IDBsOC41OC0zLjlBMSAxIDAgMCAwIDIyIDE3XCIgLz4nLFxuICAgIFwiYm94ZXNcIjogJzxwYXRoIGQ9XCJNMi45NyAxMi45MkEyIDIgMCAwIDAgMiAxNC42M3YzLjI0YTIgMiAwIDAgMCAuOTcgMS43MWwzIDEuOGEyIDIgMCAwIDAgMi4wNiAwTDEyIDE5di01LjVsLTUtMy00LjAzIDIuNDJaXCIgLz48cGF0aCBkPVwibTcgMTYuNS00Ljc0LTIuODVcIiAvPjxwYXRoIGQ9XCJtNyAxNi41IDUtM1wiIC8+PHBhdGggZD1cIk03IDE2LjV2NS4xN1wiIC8+PHBhdGggZD1cIk0xMiAxMy41VjE5bDMuOTcgMi4zOGEyIDIgMCAwIDAgMi4wNiAwbDMtMS44YTIgMiAwIDAgMCAuOTctMS43MXYtMy4yNGEyIDIgMCAwIDAtLjk3LTEuNzFMMTcgMTAuNWwtNSAzWlwiIC8+PHBhdGggZD1cIm0xNyAxNi41LTUtM1wiIC8+PHBhdGggZD1cIm0xNyAxNi41IDQuNzQtMi44NVwiIC8+PHBhdGggZD1cIk0xNyAxNi41djUuMTdcIiAvPjxwYXRoIGQ9XCJNNy45NyA0LjQyQTIgMiAwIDAgMCA3IDYuMTN2NC4zN2w1IDMgNS0zVjYuMTNhMiAyIDAgMCAwLS45Ny0xLjcxbC0zLTEuOGEyIDIgMCAwIDAtMi4wNiAwbC0zIDEuOFpcIiAvPjxwYXRoIGQ9XCJNMTIgOCA3LjI2IDUuMTVcIiAvPjxwYXRoIGQ9XCJtMTIgOCA0Ljc0LTIuODVcIiAvPjxwYXRoIGQ9XCJNMTIgMTMuNVY4XCIgLz4nLFxuICAgIFwiemFwXCI6ICc8cGF0aCBkPVwiTTQgMTRhMSAxIDAgMCAxLS43OC0xLjYzbDkuOS0xMC4yYS41LjUgMCAwIDEgLjg2LjQ2bC0xLjkyIDYuMDJBMSAxIDAgMCAwIDEzIDEwaDdhMSAxIDAgMCAxIC43OCAxLjYzbC05LjkgMTAuMmEuNS41IDAgMCAxLS44Ni0uNDZsMS45Mi02LjAyQTEgMSAwIDAgMCAxMSAxNHpcIiAvPicsXG4gICAgXCJzY3JvbGxcIjogJzxwYXRoIGQ9XCJNMTkgMTdWNWEyIDIgMCAwIDAtMi0ySDRcIiAvPjxwYXRoIGQ9XCJNOCAyMWgxMmEyIDIgMCAwIDAgMi0ydi0xYTEgMSAwIDAgMC0xLTFIMTFhMSAxIDAgMCAwLTEgMXYxYTIgMiAwIDEgMS00IDBWNWEyIDIgMCAxIDAtNCAwdjJhMSAxIDAgMCAwIDEgMWgzXCIgLz4nLFxuICAgIFwiZ2l0LW1lcmdlXCI6ICc8Y2lyY2xlIGN4PVwiMThcIiBjeT1cIjE4XCIgcj1cIjNcIiAvPjxjaXJjbGUgY3g9XCI2XCIgY3k9XCI2XCIgcj1cIjNcIiAvPjxwYXRoIGQ9XCJNNiAyMVY5YTkgOSAwIDAgMCA5IDlcIiAvPicsXG4gICAgXCJzaGllbGRcIjogJzxwYXRoIGQ9XCJNMjAgMTNjMCA1LTMuNSA3LjUtNy42NiA4Ljk1YTEgMSAwIDAgMS0uNjctLjAxQzcuNSAyMC41IDQgMTggNCAxM1Y2YTEgMSAwIDAgMSAxLTFjMiAwIDQuNS0xLjIgNi4yNC0yLjcyYTEuMTcgMS4xNyAwIDAgMSAxLjUyIDBDMTQuNTEgMy44MSAxNyA1IDE5IDVhMSAxIDAgMCAxIDEgMXpcIiAvPidcbiAgfTtcbiAgd2luZG93Ll9fbHVjaWRlID0gZnVuY3Rpb24gKG5hbWUsIHNpemUpIHtcbiAgICBzaXplID0gc2l6ZSB8fCAyNDtcbiAgICB2YXIgaW5uZXIgPSBfX2x1Y2lkZUljb25zW25hbWVdO1xuICAgIGlmICghaW5uZXIpIHJldHVybiAnJztcbiAgICByZXR1cm4gJzxzdmcgY2xhc3M9XCJsdWNpZGUgbHVjaWRlLScgKyBuYW1lICsgJ1wiIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiB3aWR0aD1cIicgKyBzaXplICsgJ1wiIGhlaWdodD1cIicgKyBzaXplICsgJ1wiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBmaWxsPVwibm9uZVwiIHN0cm9rZT1cImN1cnJlbnRDb2xvclwiIHN0cm9rZS13aWR0aD1cIjJcIiBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIj4nICsgaW5uZXIgKyAnPC9zdmc+JztcbiAgfTtcblxuICAvKiBcdTI1MDBcdTI1MDAgRGVsZWdhdGU6IGxvYWRpbmcgYnV0dG9ucyBcdTI1MDBcdTI1MDAgKi9cbiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLCBmdW5jdGlvbiAoZSkge1xuICAgIHZhciBidG4gPSBlLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1sb2FkaW5nXScpO1xuICAgIGlmIChidG4gJiYgYnRuLmdldEF0dHJpYnV0ZSgnZGF0YS1sb2FkaW5nJykpIHtcbiAgICAgIGJ0bi5pbm5lckhUTUwgPSAnUHJvY2Vzc2luZy4uLic7XG4gICAgICBidG4uZGlzYWJsZWQgPSB0cnVlO1xuICAgIH1cbiAgfSk7XG59KSgpO1xuIl0sCiAgIm1hcHBpbmdzIjogIjs7QUFBQSxHQUFDLFdBQVk7QUFDWDtBQUVBLFdBQU8sTUFBTSxPQUFPLE9BQU8sQ0FBQztBQUc1QixXQUFPLElBQUksa0JBQWtCLFNBQVUsTUFBTSxPQUFPLFlBQVk7QUFDOUQsVUFBSSxDQUFDLEtBQU07QUFDWCxVQUFJLFdBQVcsV0FBWTtBQUN6QixZQUFJLEtBQUssU0FBUyxjQUFjLFVBQVU7QUFDMUMsV0FBRyxRQUFRO0FBQ1gsV0FBRyxNQUFNLFdBQVc7QUFBUyxXQUFHLE1BQU0sT0FBTztBQUFXLFdBQUcsTUFBTSxNQUFNO0FBQ3ZFLGlCQUFTLEtBQUssWUFBWSxFQUFFO0FBQzVCLFdBQUcsT0FBTztBQUNWLFlBQUk7QUFDRixtQkFBUyxZQUFZLE1BQU07QUFDM0IsY0FBSSxPQUFPO0FBQ1QsZ0JBQUksT0FBTyxNQUFNO0FBQ2pCLGtCQUFNLFlBQWEsY0FBYztBQUNqQyxrQkFBTSxXQUFXO0FBQ2pCLHVCQUFXLFdBQVk7QUFDckIsb0JBQU0sWUFBWTtB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
