/* ── StoryBrain AI: app.js (base.js + ui-init.js bundled) ── */
/* SCHEMA localStorage keys: sb-theme ('light'|'night'), cookieConsent ('accepted'|'rejected'), sbr_tools_recent_search (JSON array) */
(function(){'use strict';const store={get(k){try{return localStorage.getItem(k)}catch{return null}},set(k,v){try{localStorage.setItem(k,v)}catch{}},del(k){try{localStorage.removeItem(k)}catch{}}};var html=document.documentElement;function setTheme(t){html.setAttribute('data-theme',t);store.set('sb-theme',t)}
document.querySelectorAll('.theme-toggle').forEach(function(b){b.addEventListener('click',function(){var c=html.getAttribute('data-theme')||'night';setTheme(c==='night'?'light':'night')})})
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){if(!store.get('sb-theme')){setTheme(e.matches?'night':'light')}})
var nav=document.getElementById('siteNavbar'),sh=document.getElementById('siteHeader');function hS(){var s=window.scrollY>20;if(nav)nav.classList.toggle('shadow-sm',s);if(sh)sh.classList.toggle('scrolled',s)}
window.addEventListener('scroll',hS,{passive:true});hS()

/* ── Nav active state for tool pages ── */
if(window.location.pathname.indexOf('/tool/')===0){document.querySelectorAll('.nav-link').forEach(function(l){if(l.getAttribute('href')==='/#tools')l.classList.add('active')})}

/* ── Tilt cards ── */
document.querySelectorAll('.tilt-card[data-tilt]').forEach(function(c){c.addEventListener('mousemove',function(e){var r=this.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-0.5,y=(e.clientY-r.top)/r.height-0.5;this.style.setProperty('--tilt-x',(-y*12)+'deg');this.style.setProperty('--tilt-y',(x*12)+'deg')});c.addEventListener('mouseleave',function(){this.style.setProperty('--tilt-x','0deg');this.style.setProperty('--tilt-y','0deg')})})

/* ── Button ripple ── */
document.querySelectorAll('.btn-ripple').forEach(function(b){b.addEventListener('mousedown',function(e){var r=this.getBoundingClientRect();this.style.setProperty('--ripple-x',((e.clientX-r.left)/r.width*100)+'%');this.style.setProperty('--ripple-y',((e.clientY-r.top)/r.height*100)+'%')})})
var dia=document.getElementById('searchDialog'),si=document.getElementById('searchInput'),sr=document.getElementById('searchResults'),toolCache=null;
function _msg(m){if(!sr)return;sr.innerHTML='';var p=document.createElement('p');p.className='text-base-content/30 text-center py-4';p.textContent=m;sr.appendChild(p)}
function _results(items){if(!sr)return;sr.innerHTML='';if(!items||!items.length){_msg('No results found');return}
var df=document.createDocumentFragment();items.slice(0,20).forEach(function(t){var a=document.createElement('a');a.setAttribute('href',typeof t.url==='string'&&t.url.charAt(0)==='/'?t.url:'#');a.className='flex items-center justify-between p-3 rounded-xl hover:glass transition-all duration-200'
var d1=document.createElement('div');var d2=document.createElement('div');d2.className='font-semibold text-sm';d2.textContent=t.name||'';d1.appendChild(d2)
var d3=document.createElement('div');d3.className='text-xs text-base-content/40';d3.textContent=t.category||'';d1.appendChild(d3);a.appendChild(d1)
var sv=document.createElementNS('http://www.w3.org/2000/svg','svg');sv.setAttribute('class','w-4 h-4 text-base-content/20');sv.setAttribute('viewBox','0 0 24 24');sv.setAttribute('fill','none');sv.setAttribute('stroke','currentColor');sv.setAttribute('stroke-width','2')
var p1=document.createElementNS('http://www.w3.org/2000/svg','path');p1.setAttribute('d','M5 12h14');sv.appendChild(p1)
var p2=document.createElementNS('http://www.w3.org/2000/svg','path');p2.setAttribute('d','m12 5 7 7-7 7');sv.appendChild(p2);a.appendChild(sv)
a.addEventListener('click',function(){if(dia)dia.close()});df.appendChild(a)});sr.appendChild(df)}
function oS(){
  if(!dia)return;
  dia.showModal();
  if(si)si.focus();
  if(!toolCache){
    fetch('/api/tools/catalog').then(function(r){return r.json()}).then(function(d){toolCache=d;filterTools()}).catch(function(){if(sr)_msg('Could not load tools. Try again later.')})
  }
}
function filterTools(){if(!si||!sr)return;var q=si.value.trim().toLowerCase();if(!toolCache||!q){_msg(q?'No results found':'Start typing to find tools');return}
var m=toolCache.filter(function(t){return t.name.toLowerCase().indexOf(q)>-1||(t.desc&&t.desc.toLowerCase().indexOf(q)>-1)})
_results(m)}
function cS(){if(dia)dia.close();document.querySelectorAll('[id^=searchToggle]').forEach(function(b){b.setAttribute('aria-expanded','false')})}
document.querySelectorAll('[id^=searchToggle]').forEach(function(b){b.setAttribute('aria-expanded','false');b.addEventListener('click',function(){oS();b.setAttribute('aria-expanded','true')})})
var hsi=document.getElementById('heroSearchInput');function openFromHero(){if(dia&&dia.open)return;var v=hsi?hsi.value:'';oS();if(si&&v){si.value=v;filterTools()}if(hsi){hsi.setAttribute('aria-expanded','true');try{hsi.blur()}catch(e){}}}if(hsi){hsi.setAttribute('aria-haspopup','dialog');hsi.setAttribute('aria-expanded','false');hsi.addEventListener('click',openFromHero);hsi.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();openFromHero()}})}
function _isEditable(el){if(!el||!el.tagName)return false;var t=el.tagName.toLowerCase();return t==='input'||t==='textarea'||t==='select'||el.isContentEditable===true}
document.addEventListener('keydown',function(e){if(e.key!=='/'||e.ctrlKey||e.metaKey||e.altKey)return;if(dia&&dia.open)return;if(_isEditable(document.activeElement))return;if(document.getElementById('toolSearchInput'))return;e.preventDefault();oS()})
var sc=document.getElementById('searchClose');if(sc)sc.addEventListener('click',cS)
if(dia){dia.addEventListener('click',function(e){if(e.target===dia)cS()});dia.addEventListener('keydown',function(e){if(e.key==='Escape')cS()});dia.addEventListener('close',function(){if(hsi)hsi.setAttribute('aria-expanded','false');document.querySelectorAll('[id^=searchToggle]').forEach(function(b){b.setAttribute('aria-expanded','false')})})}
if('serviceWorker'in navigator){var swRefreshing=false;navigator.serviceWorker.register('/service-worker',{scope:'/'}).then(function(reg){reg.addEventListener('updatefound',function(){var w=reg.installing;if(w){w.addEventListener('statechange',function(){if(w.state==='installed'&&navigator.serviceWorker.controller){var msg=document.createElement('div');msg.className='fixed bottom-4 right-4 z-50 glass-strong rounded-xl shadow-2xl border border-primary/20 animate-fade-in';msg.setAttribute('role','alert');var btn=document.createElement('button');btn.className='flex items-center gap-2 px-4 py-3 text-sm font-bold cursor-pointer focus-visible:outline-2 focus-visible:outline-primary rounded-xl';btn.innerHTML='New version available! <span class="text-primary ml-1">Refresh</span>';btn.addEventListener('click',function(){w.postMessage({action:'skipWaiting'});});btn.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();w.postMessage({action:'skipWaiting'})}});msg.appendChild(btn);document.body.appendChild(msg);btn.focus();}});}});}).catch(function(){})}navigator.serviceWorker.addEventListener('controllerchange',function(){if(swRefreshing)return;swRefreshing=true;window.location.reload();})

/* ── Dialog + accordion ── */
document.addEventListener('click',function(e){var t=e.target.closest('[data-dialog-trigger]');if(t){var id=t.dataset.dialogTrigger,dlg=document.getElementById(id);if(dlg){if(dlg.tagName==='DIALOG')dlg.showModal();else{dlg.classList.remove('hidden');dlg.classList.add('flex');document.body.style.overflow='hidden'}}return}
var cb=e.target.closest('[data-dialog-close]');if(cb){cD(cb.dataset.dialogClose);return}
var ov=e.target.closest('[data-dialog-overlay]');if(ov){var d2=ov.closest('[data-dialog]');if(d2)cD(d2.id)}})
document.addEventListener('keydown',function(e){if(e.key==='Escape'){document.querySelectorAll('[data-dialog]:not(.hidden)').forEach(function(d){cD(d.id)})}})
function cD(id){var dlg=document.getElementById(id);if(dlg){if(dlg.tagName==='DIALOG')dlg.close();else{dlg.classList.add('hidden');dlg.classList.remove('flex');document.body.style.overflow=''}}}
function toggleAccordion(t){var ac=t.closest('[data-accordion]');if(!ac)return;var it=t.closest('[data-accordion-item]'),isOpen=it?it.dataset.open==='true':false
if(ac.dataset.accordion!=='multi'){ac.querySelectorAll('[data-accordion-item]').forEach(function(i){i.dataset.open='false';var c=i.querySelector('[data-accordion-content]');if(c){c.style.display='none';c.style.maxHeight='0'}
var ch=i.querySelector('[data-accordion-chevron]');if(ch)ch.classList.remove('rotate-180');var tr=i.querySelector('[data-accordion-trigger]');if(tr)tr.setAttribute('aria-expanded','false')})}
if(it){var nO=isOpen?'false':'true';it.dataset.open=nO;var c2=it.querySelector('[data-accordion-content]');if(c2){c2.style.display=nO==='true'?'block':'none';c2.style.maxHeight=nO==='true'?c2.scrollHeight+'px':'0'}
var ch2=it.querySelector('[data-accordion-chevron]');if(ch2)ch2.classList.toggle('rotate-180',nO==='true');t.setAttribute('aria-expanded',nO)}}
document.addEventListener('click',function(e){var t=e.target.closest('[data-accordion-trigger]');if(t){e.preventDefault();toggleAccordion(t)}})
document.addEventListener('keydown',function(e){if(e.key!=='Enter'&&e.key!==' ')return;var t=e.target.closest('[data-accordion-trigger]');if(t){e.preventDefault();toggleAccordion(t)}})
document.querySelectorAll('[data-accordion-item][data-open="true"]').forEach(function(it){var c=it.querySelector('[data-accordion-content]');if(c){c.style.display='block';c.style.maxHeight=c.scrollHeight+'px'}
var ch=it.querySelector('[data-accordion-chevron]');if(ch)ch.classList.add('rotate-180')})
document.querySelectorAll('.dropdown button[aria-haspopup="true"]').forEach(function(b){b.addEventListener('click',function(){var d=b.closest('.dropdown'),c=d?d.querySelector('.dropdown-content'):null;if(c){var o=c.style.display!=='block';c.style.display=o?'block':'';b.setAttribute('aria-expanded',o)}})})

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

/* ── Legacy Hover-Intent Prefetching Removed (Using Speculation Rules instead) ── */

/* ── Hero mouse-follow glow ── */
var hs=document.getElementById('heroSection');if(hs){var _r=null,_rid=!1;hs.addEventListener('mousemove',function(e){if(_rid)cancelAnimationFrame(_r);_rid=!0;_r=requestAnimationFrame(function(){var b=hs.getBoundingClientRect(),mx=(e.clientX-b.left)/b.width*100,my=(e.clientY-b.top)/b.height*100;hs.style.setProperty('--mx',mx+'%');hs.style.setProperty('--my',my+'%');_rid=!1})},{passive:!0})}
})();
