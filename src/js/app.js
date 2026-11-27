/* ── StoryBrain AI: app.js (Alpine.js + UI bundle) ── */
import Alpine from 'alpinejs';

// Expose Alpine globally
window.Alpine = Alpine;

// Global formatting and helper utilities for Alpine reactive expressions
window.formatCurrency = function(val, dec) {
  var n = parseFloat(val);
  if (isNaN(n)) return '$0.00';
  var d = dec !== undefined ? dec : 2;
  var sign = n < 0 ? '-$' : '$';
  return sign + Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
};

window.formatNumber = function(val, dec) {
  var n = parseFloat(val);
  if (isNaN(n)) return '0';
  var d = dec !== undefined ? dec : 0;
  return n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
};

// Alpine Global Store: Mobile Drawer
Alpine.store('drawer', {
  open: false,
  toggle() {
    this.open = !this.open;
    document.body.classList.toggle('overflow-hidden', this.open);
  },
  close() {
    this.open = false;
    document.body.classList.remove('overflow-hidden');
  }
});

// Alpine Global Store: Theme Switcher
Alpine.store('theme', {
  current: (function() {
    try {
      return localStorage.getItem('sb-theme') || document.documentElement.getAttribute('data-theme') || 'dark';
    } catch(e) {
      return 'dark';
    }
  })(),
  toggle() {
    this.current = (this.current === 'dark' || this.current === 'night') ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', this.current);
    try { localStorage.setItem('sb-theme', this.current); } catch(e) {}
  }
});

// Alpine Global Component: Cookie Consent
Alpine.data('cookieConsent', function() {
  return {
    show: false,
    init: function() {
      var gpc = navigator.globalPrivacyControl === true || window.globalPrivacyControl === true;
      window.__sbrGpcEnabled = gpc;
      if (gpc) return;
      var consent = null;
      try { consent = localStorage.getItem('cookieConsent'); } catch(e) {}
      if (!consent) {
        var self = this;
        setTimeout(function() { self.show = true; }, 1000);
      }
    },
    accept: function() {
      try { localStorage.setItem('cookieConsent', 'accepted'); } catch(e) {}
      this.show = false;
      window.dispatchEvent(new Event('cookieConsentGiven'));
    },
    reject: function() {
      try { localStorage.setItem('cookieConsent', 'rejected'); } catch(e) {}
      this.show = false;
    }
  };
});

// Alpine Global Component: Omni Search Modal
Alpine.data('omniSearch', function() {
  return {
    q: '',
    status: 'empty', // 'empty' | 'results' | 'no-results' | 'error'
    results: [],
    tools: null,
    init: function() {
      var self = this;
      window.openOmniSearch = function() { self.show(); };
      document.addEventListener('keydown', function(e) {
        if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
          e.preventDefault();
          var tsi = document.getElementById('toolSearchInput');
          if (tsi) {
            tsi.focus();
            tsi.scrollIntoView({ block: 'center', behavior: 'smooth' });
          } else {
            self.show();
          }
          return;
        }
        if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
          var el = document.activeElement;
          var tag = el ? el.tagName.toLowerCase() : '';
          if (tag === 'input' || tag === 'textarea' || (el && el.isContentEditable)) return;
          var tsi2 = document.getElementById('toolSearchInput');
          if (tsi2) {
            e.preventDefault();
            tsi2.focus();
            tsi2.scrollIntoView({ block: 'center', behavior: 'smooth' });
            return;
          }
          e.preventDefault();
          self.show();
        }
      });
    },
    show: function() {
      var dia = this.$el || document.getElementById('searchDialog');
      if (dia && !dia.open && dia.showModal) {
        dia.showModal();
        var si = (this.$refs && this.$refs.searchInput) || document.getElementById('searchInput');
        if (si) setTimeout(function() { si.focus(); }, 50);
      }
      if (!this.tools) {
        var self = this;
        fetch('/api/tools/catalog')
          .then(function(r) { if (!r.ok) throw new Error('catalog ' + r.status); return r.json(); })
          .then(function(d) {
            self.tools = Array.isArray(d) ? d : (d && Array.isArray(d.tools) ? d.tools : []);
            self.filter();
          })
          .catch(function() {
            self.tools = [];
            self.status = 'error';
          });
      }
    },
    close: function() {
      var dia = this.$el || document.getElementById('searchDialog');
      if (dia && dia.open && dia.close) dia.close();
      document.querySelectorAll('[id^=searchToggle]').forEach(function(b) {
        b.setAttribute('aria-expanded', 'false');
      });
    },
    filter: function() {
      var query = this.q.trim().toLowerCase();
      if (!query) {
        this.status = 'empty';
        this.results = [];
        return;
      }
      if (!Array.isArray(this.tools)) {
        this.status = 'error';
        return;
      }
      var matches = this.tools.filter(function(t) {
        var n = (t && t.name ? t.name : '').toLowerCase();
        var d = (t && t.desc ? t.desc : '').toLowerCase();
        var c = (t && t.category ? t.category : '').toLowerCase();
        return n.indexOf(query) > -1 || d.indexOf(query) > -1 || c.indexOf(query) > -1;
      });
      if (!matches.length) {
        this.status = 'no-results';
        this.results = [];
      } else {
        this.status = 'results';
        this.results = matches.slice(0, 20);
      }
    }
  };
});

// Alpine Global Component: Accordion
Alpine.data('accordion', function(defaultOpen) {
  return {
    open: Boolean(defaultOpen),
    toggle: function() {
      this.open = !this.open;
    }
  };
});

// Alpine Global Component: Copy Button
Alpine.data('copyButton', function(defaultText) {
  return {
    copied: false,
    copy: function(val) {
      var txt = val || defaultText || window.location.href;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        var self = this;
        navigator.clipboard.writeText(txt).then(function() {
          self.copied = true;
          setTimeout(function() { self.copied = false; }, 1800);
        }).catch(function() {});
      }
    }
  };
});

// Alpine Global Component: Tool Helpfulness Tracker
Alpine.data('helpfulWidget', function(slug) {
  var s = slug || window.location.pathname;
  return {
    done: false,
    init: function() {
      try {
        this.done = localStorage.getItem('sb_helpful_' + s) === '1';
      } catch (e) {
        this.done = false;
      }
    },
    vote: function(v) {
      if (this.done) return;
      try {
        var payload = JSON.stringify({ name: s + ':helpful-' + v, category: v === 'yes' ? 'helpful_yes' : 'helpful_no' });
        if (navigator.sendBeacon) {
          navigator.sendBeacon('/api/track', new Blob([payload], { type: 'application/json' }));
        } else {
          fetch('/api/track', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true });
        }
      } catch (err) {}
      this.done = true;
      try { localStorage.setItem('sb_helpful_' + s, '1'); } catch (e) {}
    }
  };
});

// Start Alpine
Alpine.start();

/* SCHEMA localStorage keys: sb-theme ('light'|'night'), cookieConsent ('accepted'|'rejected'), sbr_tools_recent_search (JSON array) */
(function(){'use strict';const store={get(k){try{return localStorage.getItem(k)}catch{return null}},set(k,v){try{localStorage.setItem(k,v)}catch{}},del(k){try{localStorage.removeItem(k)}catch{}}};var html=document.documentElement;function setTheme(t){html.setAttribute('data-theme',t);store.set('sb-theme',t)}
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){if(!store.get('sb-theme')){setTheme(e.matches?'dark':'light')}})
var nav=document.getElementById('siteNavbar'),sh=document.getElementById('siteHeader');function hS(){var s=window.scrollY>20;if(nav)nav.classList.toggle('shadow-sm',s);if(sh)sh.classList.toggle('scrolled',s)}
window.addEventListener('scroll',hS,{passive:true});if(typeof requestAnimationFrame==='function')requestAnimationFrame(hS);

/* ── Nav active state for tool pages ── */
if(window.location.pathname.indexOf('/tool/')===0){document.querySelectorAll('.nav-link').forEach(function(l){if(l.getAttribute('href')==='/#tools')l.classList.add('active')})}

/* ── Tilt cards ── */
document.querySelectorAll('.tilt-card[data-tilt]').forEach(function(c){c.addEventListener('mousemove',function(e){var r=this.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-0.5,y=(e.clientY-r.top)/r.height-0.5;this.style.setProperty('--tilt-x',(-y*12)+'deg');this.style.setProperty('--tilt-y',(x*12)+'deg')});c.addEventListener('mouseleave',function(){this.style.setProperty('--tilt-x','0deg');this.style.setProperty('--tilt-y','0deg')})})

/* ── Button ripple ── */
document.querySelectorAll('.btn-ripple').forEach(function(b){b.addEventListener('mousedown',function(e){var r=this.getBoundingClientRect();this.style.setProperty('--ripple-x',((e.clientX-r.left)/r.width*100)+'%');this.style.setProperty('--ripple-y',((e.clientY-r.top)/r.height*100)+'%')})})

if('serviceWorker'in navigator){navigator.serviceWorker.getRegistrations().then(function(regs){for(var i=0;i<regs.length;i++){regs[i].unregister()}}).catch(function(){});if(window.caches){caches.keys().then(function(keys){for(var j=0;j<keys.length;j++){caches.delete(keys[j])}}).catch(function(){})}}

/* ── Scroll reveal IntersectionObserver (with no-JS/no-IO fallback: reveal all) ── */
if('IntersectionObserver'in window){var ro=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');ro.unobserve(e.target)}})},{threshold:0.1})
document.querySelectorAll('.reveal').forEach(function(el){ro.observe(el)})}
else{document.querySelectorAll('.reveal').forEach(function(el){el.classList.add('visible')})}

/* ── Lightweight analytics ── */
var an=document.getElementById('analytics-track');if(an&&'sendBeacon'in navigator){var b=new Blob([JSON.stringify({name:an.dataset.tool||'page',category:'page_view'})],{type:'application/json'});navigator.sendBeacon('/api/track',b)}



/* ── CSP-safe delegated actions (replaces inline onclick="...") ──
   Covers: meme_generator, qr_generator, sitemap_generator, image_background_remover,
   crypto_fear_greed. Tool-local el.onclick= property assignments are kept as-is. */
document.addEventListener('click',function(e){
  var el=e.target&&e.target.closest?e.target.closest('[data-action]'):null;
  if(!el)return;
  var a=el.getAttribute('data-action'),w=window;
  function idx(){var v=parseInt(el.getAttribute('data-index'),10);return isNaN(v)?0:v}
  if(a==='close-dialog'){var t=el.getAttribute('data-target'),d=t&&document.getElementById(t);if(d&&d.close)d.close();return}
  if(a==='close-zoom'){el.classList.remove('open');return}
  if(a==='refresh-fng'){return} /* tool script owns fetchLive via #refreshBtn listener */
  if(a==='meme-preset'){if(typeof w.applyPreset==='function')w.applyPreset(el.getAttribute('data-preset'));return}
  if(a==='meme-download'){if(typeof w.downloadMeme==='function')w.downloadMeme();return}
  if(a==='meme-copy'){if(typeof w.copyMeme==='function')w.copyMeme();return}
  if(a==='meme-clear-hist'){if(typeof w.clearHist==='function')w.clearHist();return}
  if(a==='meme-restore-hist'){if(typeof w.restoreHist==='function')w.restoreHist(idx());return}
  if(a==='meme-del-hist'){if(typeof w.delHist==='function')w.delHist(idx());return}
  if(a==='qr-dot-style'){if(typeof w.setDotStyle==='function')w.setDotStyle(el.getAttribute('data-style'),el);return}
  if(a==='qr-eye-style'){if(typeof w.setEyeStyle==='function')w.setEyeStyle(el.getAttribute('data-style'),el);return}
  if(a==='qr-clear-logo'){if(typeof w.clearLogo==='function')w.clearLogo();return}
  if(a==='qr-scan'){if(typeof w.scanQR==='function')w.scanQR();return}
  if(a==='qr-fill-scan'){if(typeof w.fillFromScan==='function')w.fillFromScan();return}
  if(a==='qr-gen'){if(typeof w.gen==='function')w.gen();return}
  if(a==='qr-download-png'){if(typeof w.downloadPNG==='function')w.downloadPNG();return}
  if(a==='qr-download-svg'){if(typeof w.downloadSVG==='function')w.downloadSVG();return}
  if(a==='qr-copy-png'){if(typeof w.copyPNG==='function')w.copyPNG();return}
  if(a==='qr-copy-svg'){if(typeof w.copySVGCode==='function')w.copySVGCode();return}
  if(a==='qr-clear-hist'){if(typeof w.clearHist==='function')w.clearHist();return}
  if(a==='qr-restore-hist'){if(typeof w.restoreHist==='function')w.restoreHist(idx());return}
  if(a==='qr-apply-preset'){if(typeof w.applyPreset==='function')w.applyPreset(el.getAttribute('data-fg'),el.getAttribute('data-bg'));return}
});

/* ── Legacy Hover-Intent Prefetching & Duplicate Helpfulness Handler Removed (Handled by Speculation Rules & Alpine helpfulWidget) ── */

/* ── Hero mouse-follow glow ── */
var hs=document.getElementById('heroSection');if(hs){var _r=null,_rid=!1;hs.addEventListener('mousemove',function(e){if(_rid)cancelAnimationFrame(_r);_rid=!0;_r=requestAnimationFrame(function(){var b=hs.getBoundingClientRect(),mx=(e.clientX-b.left)/b.width*100,my=(e.clientY-b.top)/b.height*100;hs.style.setProperty('--mx',mx+'%');hs.style.setProperty('--my',my+'%');_rid=!1})},{passive:!0})}
})();
