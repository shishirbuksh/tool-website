/* ── StoryBrain AI: app.js (base.js + ui-init.js bundled) ── */
(function(){'use strict';var html=document.documentElement;function setTheme(t){html.setAttribute('data-theme',t);localStorage.setItem('sb-theme',t)}
document.querySelectorAll('.theme-toggle').forEach(function(b){b.addEventListener('click',function(){var c=html.getAttribute('data-theme')||'night';setTheme(c==='night'?'light':'night')})})
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(e){if(!localStorage.getItem('sb-theme')){setTheme(e.matches?'night':'light')}})
var nav=document.getElementById('siteNavbar'),sh=document.getElementById('siteHeader');function hS(){var s=window.scrollY>20;if(nav)nav.classList.toggle('shadow-sm',s);if(sh)sh.classList.toggle('scrolled',s)}
window.addEventListener('scroll',hS,{passive:true});hS()

/* ── Nav active state for tool pages ── */
if(window.location.pathname.indexOf('/tool/')===0){document.querySelectorAll('.nav-link').forEach(function(l){if(l.getAttribute('href')==='/tools')l.classList.add('active')})}

/* ── Tilt cards ── */
document.querySelectorAll('.tilt-card[data-tilt]').forEach(function(c){c.addEventListener('mousemove',function(e){var r=this.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-0.5,y=(e.clientY-r.top)/r.height-0.5;this.style.setProperty('--tilt-x',(-y*12)+'deg');this.style.setProperty('--tilt-y',(x*12)+'deg')});c.addEventListener('mouseleave',function(){this.style.setProperty('--tilt-x','0deg');this.style.setProperty('--tilt-y','0deg')})})

/* ── Button ripple ── */
document.querySelectorAll('.btn-ripple').forEach(function(b){b.addEventListener('mousedown',function(e){var r=this.getBoundingClientRect();this.style.setProperty('--ripple-x',((e.clientX-r.left)/r.width*100)+'%');this.style.setProperty('--ripple-y',((e.clientY-r.top)/r.height*100)+'%')})})
var dia=document.getElementById('searchDialog'),si=document.getElementById('searchInput')
function oS(){
  if(!dia)return;
  dia.showModal();
  if(si)si.focus();
  // Fetch tool catalog if not already cached
  if(!toolCache){
    fetch('/api/tools/catalog').then(function(r){return r.json()}).then(function(d){toolCache=d;filterTools()}).catch(function(){if(sr)sr.innerHTML='<p class="text-base-content/30 text-center py-4">Could not load tools. Try again later.</p>'})
  }
}
function cS(){if(dia)dia.close()}
document.querySelectorAll('[id^=searchToggle]').forEach(function(b){b.addEventListener('click',oS)})
var hsi=document.getElementById('heroSearchInput');if(hsi){hsi.addEventListener('click',function(e){e.preventDefault();if(!dia.open)oS()})}
var sc=document.getElementById('searchClose');if(sc)sc.addEventListener('click',cS)
if(dia){dia.addEventListener('click',function(e){if(e.target===dia)cS()});dia.addEventListener('keydown',function(e){if(e.key==='Escape')cS()})}
var eb=document.getElementById('exploreToolsBtn');if(eb){eb.addEventListener('click',function(){var d=document.getElementById('mobileDrawer');if(d)d.checked=true})}
if('serviceWorker'in navigator){var swRefreshing=false;navigator.serviceWorker.register('/sw.js',{scope:'/'}).then(function(reg){reg.addEventListener('updatefound',function(){var w=reg.installing;if(w){w.addEventListener('statechange',function(){if(w.state==='installed'&&navigator.serviceWorker.controller){var msg=document.createElement('div');msg.className='fixed bottom-4 right-4 z-50 glass-strong rounded-xl shadow-2xl border border-primary/20 animate-fade-in';msg.setAttribute('role','alert');var btn=document.createElement('button');btn.className='flex items-center gap-2 px-4 py-3 text-sm font-bold cursor-pointer focus-visible:outline-2 focus-visible:outline-primary rounded-xl';btn.innerHTML='New version available! <span class="text-primary ml-1">Refresh</span>';btn.addEventListener('click',function(){w.postMessage({action:'skipWaiting'});});btn.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();w.postMessage({action:'skipWaiting'})}});msg.appendChild(btn);document.body.appendChild(msg);btn.focus();}});}});}).catch(function(){})}navigator.serviceWorker.addEventListener('controllerchange',function(){if(swRefreshing)return;swRefreshing=true;window.location.reload();})

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

/* ── Scroll reveal IntersectionObserver ── */
if('IntersectionObserver'in window){var ro=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');ro.unobserve(e.target)}})},{threshold:0.1})
document.querySelectorAll('.reveal').forEach(function(el){ro.observe(el)})}

/* ── Lightweight analytics ── */
var an=document.getElementById('analytics-track');if(an&&'sendBeacon'in navigator){var b=new Blob([JSON.stringify({name:an.dataset.tool||'page',category:'page_view'})],{type:'application/json'});navigator.sendBeacon('/api/track',b)}

/* ── Search dialog ── */
var sd=document.getElementById('searchDialog'),si=document.getElementById('searchInput'),sr=document.getElementById('searchResults'),toolCache=null;
if(sd&&si&&sr){sd.addEventListener('open',function(){if(!toolCache){fetch('/api/tools/catalog').then(function(r){return r.json()}).then(function(d){toolCache=d;filterTools()}).catch(function(){sr.innerHTML='<p class="text-base-content/30 text-center py-4">Could not load tools. Try again later.</p>'})}})
si.addEventListener('input',function(){filterTools()})}
function filterTools(){var q=si.value.trim().toLowerCase();if(!toolCache||!q){sr.innerHTML='<p class="text-base-content/30 text-center py-4">'+(q?'No results found':'Start typing to find tools')+'</p>';return}
var m=toolCache.filter(function(t){return t.name.toLowerCase().indexOf(q)>-1||(t.desc&&t.desc.toLowerCase().indexOf(q)>-1)})
if(m.length===0){sr.innerHTML='<p class="text-base-content/30 text-center py-4">No results found</p>';return}
sr.innerHTML=m.slice(0,20).map(function(t){return'<a href="'+t.url+'" class="flex items-center justify-between p-3 rounded-xl hover:glass transition-all duration-200" onclick="document.getElementById(\'searchDialog\').close()"><div><div class="font-semibold text-sm">'+t.name+'</div><div class="text-xs text-base-content/40">'+t.category+'</div></div><svg class="w-4 h-4 text-base-content/20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg></a>'}).join('')}

/* ── Hero mouse-follow glow ── */
var hs=document.getElementById('heroSection');if(hs){var _r=null,_rid=!1;hs.addEventListener('mousemove',function(e){if(_rid)cancelAnimationFrame(_r);_rid=!0;_r=requestAnimationFrame(function(){var b=hs.getBoundingClientRect(),mx=(e.clientX-b.left)/b.width*100,my=(e.clientY-b.top)/b.height*100;hs.style.setProperty('--mx',mx+'%');hs.style.setProperty('--my',my+'%');_rid=!1})},{passive:!0})}
})();
