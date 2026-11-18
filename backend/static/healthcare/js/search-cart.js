/**
 * search-cart.js — Synchronisation panier/chariot (session / patient)
 * Extrait de search.html — Phase 2 refacto MedCare
 */
(function(){
  'use strict';

  var cfg = window.SIPN_CONFIG || {};
  var urls = cfg.urls || {};
  var demAssuranceCtx = cfg.demAssuranceCtx || null;

  var cards = Array.prototype.slice.call(document.querySelectorAll('.scard[data-pa-id], .scard-m-acte[data-pa-id]'))
    .filter(function(c){ return c.getAttribute('data-ambulance-acte') !== '1'; });
  var cartCountEls = document.querySelectorAll('[data-dem-cart-count]');
  var cartBodyEls = document.querySelectorAll('[data-dem-cart-body]');
  var cartFloatWrapEl = document.getElementById('cart-float-wrap');
  if (!cartCountEls.length && !cartBodyEls.length && !cartFloatWrapEl) return;

  function getCsrfToken() {
    return window.SIPNUtils ? window.SIPNUtils.getCsrfToken() : (document.querySelector('input[name="csrfmiddlewaretoken"]') || {}).value || '';
  }

  function sipnIconSvg(name, cls) {
    var paths = {
      cart: 'M2.25 3h1.386c.512 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 0 0-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 0 0-16.536-1.84M7.5 14.25 5.106 5.272M6 20.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Zm12.75 0a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z',
      calendar: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5',
      chat: 'M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z',
      clock: 'M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
      warning: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.732 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.008v.008H12v-.008Z',
      shield: 'M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z',
      home: 'm2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25'
    };
    var d = paths[name];
    if (!d) return '';
    return '<svg class="' + (cls || 'sipn-ico sipn-ico--xs') + '" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="' + d + '"/></svg>';
  }

  var cartRemoveFallbackTpl = urls.cartRemoveFallbackTpl || '/cart/remove/pa/999001999/';
  function assuranceQuerySuffix(){
    if (!demAssuranceCtx || !demAssuranceCtx.ids || !demAssuranceCtx.ids.length) return '';
    return demAssuranceCtx.ids.map(function(id){ return 'assurance=' + encodeURIComponent(id); }).join('&');
  }
  function appendAssuranceQs(url){
    var qs = assuranceQuerySuffix();
    if (!qs) return url;
    return url + (url.indexOf('?') >= 0 ? '&' : '?') + qs;
  }
  function applyCartCoverage(data){
    cartCoverage = (data && data.coverage) ? data.coverage : null;
  }
  function removeUrlForPaId(id){
    var c = document.querySelector('.scard[data-pa-id="' + id + '"], .scard-m-acte[data-pa-id="' + id + '"]');
    var u = c && c.getAttribute('data-pa-remove-url');
    if (u) return u;
    return cartRemoveFallbackTpl.replace('999001999', String(id));
  }

  function syncCartBadges(count){
    var n = Math.max(0, parseInt(count, 10) || 0);
    document.querySelectorAll('.medcare-cart-badge').forEach(function(el){
      el.textContent = String(n);
      el.classList.toggle('hidden', n === 0);
    });
    document.querySelectorAll('.medcare-cart-pac-mob').forEach(function(el){
      el.textContent = String(n);
    });
    document.querySelectorAll('.medcare-cart-pac-mob-wrap').forEach(function(el){
      el.classList.toggle('hidden', n === 0);
    });
    document.querySelectorAll('[data-bnav-dot="panier"]').forEach(function(el){
      el.classList.toggle('show', n > 0);
    });
    document.querySelectorAll('.mc-landing-drawer-badge').forEach(function(el){
      el.textContent = String(n);
      el.classList.toggle('hidden', n === 0);
    });
    document.querySelectorAll('.sb-badge').forEach(function(el){
      if (el.closest('.sb-link') && el.closest('.sb-link').textContent.includes('Panier')) {
        el.textContent = String(n);
        el.classList.toggle('hidden', n === 0);
      }
    });
  }

  var cart = new Map();
  var cartCoverage = null;
  var cartDevisBaseUrl = urls.cartDevisBaseUrl || '/cart/devis/';
  var cartViewUrl = urls.cartViewUrl || '/cart/';
  var cartChariotUrl = urls.cartChariotUrl || null;
  var cartLoginUrl = urls.cartLoginUrl || '/accounts/login/';
  function fnum(v){ return Math.round(Number(v || 0)).toLocaleString('fr-FR'); }
  function escapeHtml(s){ var d = document.createElement('div'); d.textContent = String(s || ''); return d.innerHTML; }
  function cartQuantity(item){
    var quantity = parseInt(item && item.quantity, 10);
    return isNaN(quantity) || quantity < 1 ? 1 : quantity;
  }
  function cartUnits(items){
    return items.reduce(function(total, item){ return total + cartQuantity(item); }, 0);
  }
  function cartTotal(items){
    return items.reduce(function(total, item){ return total + item.price * cartQuantity(item); }, 0);
  }
  function devisConfirmText(orgName, items){
    var lines = items.map(function(item){
      return item.acte + (cartQuantity(item) > 1 ? ' ×' + cartQuantity(item) : '');
    });
    return 'Envoyer une demande à ' + orgName + ' pour tous les actes suivants : '
      + lines.join('; ') + '. Total estimé : ' + fnum(cartTotal(items)) + ' FCFA. Continuer ?';
  }

  /* ── Tri-Tarifs Switcher (Comptant / IPM / Assurance / Multi-sélection État D) ── */
  var activeTriTarifRegimes = ['comptant'];

  function parseTriTarifRegimes(val) {
    if (!val) return ['comptant'];
    if (Array.isArray(val)) return val;
    if (typeof val === 'string') {
      var parts = val.toLowerCase().split(',').map(function(s){ return s.trim(); }).filter(Boolean);
      return parts.length ? parts : ['comptant'];
    }
    return ['comptant'];
  }

  function setTriTarifRegime(regimesInput) {
    var regimes = parseTriTarifRegimes(regimesInput);
    var isComptant = regimes.indexOf('comptant') !== -1 || (regimes.indexOf('ipm') === -1 && regimes.indexOf('assurance') === -1);
    var hasIpm = !isComptant && regimes.indexOf('ipm') !== -1;
    var hasAssurance = !isComptant && regimes.indexOf('assurance') !== -1;

    if (isComptant) {
      activeTriTarifRegimes = ['comptant'];
    } else {
      activeTriTarifRegimes = [];
      if (hasIpm) activeTriTarifRegimes.push('ipm');
      if (hasAssurance) activeTriTarifRegimes.push('assurance');
    }

    var btns = document.querySelectorAll('.tritarif-chip-btn');
    btns.forEach(function(btn) {
      var r = btn.getAttribute('data-regime');
      var isActive = (r === 'comptant' && isComptant) ||
                     (r === 'ipm' && hasIpm) ||
                     (r === 'assurance' && hasAssurance);
      if (isActive) {
        btn.className = 'tritarif-chip-btn rounded-lg px-3 py-1.5 transition-all bg-white text-gray-900 shadow-xs font-bold ring-1 ring-gray-200';
        btn.setAttribute('aria-pressed', 'true');
      } else {
        btn.className = 'tritarif-chip-btn rounded-lg px-3 py-1.5 transition-all text-gray-600 hover:text-gray-900 font-medium';
        btn.setAttribute('aria-pressed', 'false');
      }
    });

    var hintEl = document.getElementById('tritarif-regime-hint');
    if (hintEl) {
      if (hasIpm && hasAssurance) {
        hintEl.textContent = "Multi-sélection : IPM & Assurance comparées par acte";
      } else if (hasIpm) {
        hintEl.textContent = "Tarifs conventionnés IPM & statuts de prise en charge";
      } else if (hasAssurance) {
        hintEl.textContent = "Tarifs conventionnés Assurance & statuts de prise en charge";
      } else {
        hintEl.textContent = "Tarifs publics au comptant";
      }
    }

    var items = document.querySelectorAll('.acte-item, .scard-m-acte');
    items.forEach(function(item) {
      var basePrice = item.getAttribute('data-pa-price');
      var priceIpm = item.getAttribute('data-pa-price-ipm');
      var priceAssurance = item.getAttribute('data-pa-price-assurance');
      var statusIpm = item.getAttribute('data-pa-status-ipm') || 'to_confirm';
      var statusAssurance = item.getAttribute('data-pa-status-assurance') || 'to_confirm';

      if (statusIpm === 'covered' && (!priceIpm || Number(priceIpm) <= 0)) {
        statusIpm = 'to_confirm';
      }
      if (statusAssurance === 'covered' && (!priceAssurance || Number(priceAssurance) <= 0)) {
        statusAssurance = 'to_confirm';
      }

      var prixEl = item.querySelector('.ai-prix, .scard-m-acte-prix');
      var badgeEl = item.querySelector('.ai-regime-badge');
      if (!prixEl) return;

      if (isComptant) {
        prixEl.textContent = fnum(basePrice) + ' FCFA';
        if (badgeEl) {
          badgeEl.style.display = 'none';
          badgeEl.innerHTML = '';
        }
      } else if (hasIpm && hasAssurance) {
        var htmlBadges = '';

        if (statusIpm === 'excluded') {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-rose-700 bg-rose-50 border border-rose-200">✕ IPM non couvert</span>';
        } else if (statusIpm === 'covered' && priceIpm && Number(priceIpm) > 0) {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200">✓ IPM ' + fnum(priceIpm) + ' F</span>';
        } else {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200">⚑ IPM à confirmer</span>';
        }

        if (statusAssurance === 'excluded') {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-rose-700 bg-rose-50 border border-rose-200">✕ Assur. non couvert</span>';
        } else if (statusAssurance === 'covered' && priceAssurance && Number(priceAssurance) > 0) {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200">✓ Assur. ' + fnum(priceAssurance) + ' F</span>';
        } else {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200">⚑ Assur. à confirmer</span>';
        }

        var hasCoveredTarif = (statusIpm === 'covered' && priceIpm && Number(priceIpm) > 0) ||
                              (statusAssurance === 'covered' && priceAssurance && Number(priceAssurance) > 0);
        if (!hasCoveredTarif) {
          htmlBadges += '<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-gray-700 bg-gray-100 border border-gray-200">Comptant ' + fnum(basePrice) + ' F</span>';
          prixEl.textContent = fnum(basePrice) + ' FCFA';
        } else {
          prixEl.textContent = '';
        }

        if (badgeEl) {
          badgeEl.style.display = 'flex';
          badgeEl.className = 'ai-regime-badge mt-1 flex flex-wrap items-center justify-end gap-1';
          badgeEl.innerHTML = htmlBadges;
        }
      } else if (hasIpm) {
        if (statusIpm === 'excluded') {
          prixEl.textContent = fnum(basePrice) + ' FCFA';
          if (badgeEl) {
            badgeEl.style.display = 'block';
            badgeEl.className = 'ai-regime-badge mt-0.5 text-[10px] font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded';
            badgeEl.textContent = '✕ Non couvert · Comptant';
          }
        } else if (statusIpm === 'covered' && priceIpm && Number(priceIpm) > 0) {
          prixEl.textContent = fnum(priceIpm) + ' FCFA';
          if (badgeEl) {
            badgeEl.style.display = 'block';
            badgeEl.className = 'ai-regime-badge mt-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded';
            badgeEl.textContent = '✓ Conventionné IPM';
          }
        } else {
          prixEl.textContent = fnum(basePrice) + ' FCFA';
          if (badgeEl) {
            badgeEl.style.display = 'block';
            badgeEl.className = 'ai-regime-badge mt-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded';
            badgeEl.textContent = '⚑ À confirmer IPM';
          }
        }
      } else if (hasAssurance) {
        if (statusAssurance === 'excluded') {
          prixEl.textContent = fnum(basePrice) + ' FCFA';
          if (badgeEl) {
            badgeEl.style.display = 'block';
            badgeEl.className = 'ai-regime-badge mt-0.5 text-[10px] font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded';
            badgeEl.textContent = '✕ Non couvert · Comptant';
          }
        } else if (statusAssurance === 'covered' && priceAssurance && Number(priceAssurance) > 0) {
          prixEl.textContent = fnum(priceAssurance) + ' FCFA';
          if (badgeEl) {
            badgeEl.style.display = 'block';
            badgeEl.className = 'ai-regime-badge mt-0.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded';
            badgeEl.textContent = '✓ Conventionné Assurance';
          }
        } else {
          prixEl.textContent = fnum(basePrice) + ' FCFA';
          if (badgeEl) {
            badgeEl.style.display = 'block';
            badgeEl.className = 'ai-regime-badge mt-0.5 text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded';
            badgeEl.textContent = '⚑ À confirmer Assurance';
          }
        }
      }
    });
  }

  document.addEventListener('click', function(e) {
    var btn = e.target && e.target.closest && e.target.closest('.tritarif-chip-btn');
    if (!btn) return;
    var clickedRegime = (btn.getAttribute('data-regime') || '').toLowerCase().trim();
    var nextRegimes = [];

    if (clickedRegime === 'comptant') {
      nextRegimes = ['comptant'];
    } else {
      var currentWithoutComptant = activeTriTarifRegimes.filter(function(r){ return r !== 'comptant'; });
      var exists = currentWithoutComptant.indexOf(clickedRegime) !== -1;
      if (exists) {
        nextRegimes = currentWithoutComptant.filter(function(r){ return r !== clickedRegime; });
      } else {
        nextRegimes = currentWithoutComptant.concat([clickedRegime]);
      }
      if (!nextRegimes.length) {
        nextRegimes = ['comptant'];
      }
    }

    setTriTarifRegime(nextRegimes);
    try {
      sessionStorage.setItem('mc_regime', nextRegimes.join(','));
    } catch(ignored) {}
  });

  (function() {
    var stored = sessionStorage.getItem('mc_regime');
    if (stored) {
      var regs = parseTriTarifRegimes(stored);
      setTriTarifRegime(regs);
    }
  })();

  (function() {
    var form = document.getElementById('search-form');
    if (form) {
      form.addEventListener('submit', function() {
        try { sessionStorage.removeItem('mc_regime'); } catch(ignored) {}
      });
    }
  })();

  function sipnToast(msg, level){
    var text = String(msg || '');
    if (!text) return;
    if (window.MedcareUI && typeof MedcareUI.toast === 'function') {
      MedcareUI.toast(text, {
        level: level || 'info',
        duration: (level === 'error' || level === 'warning') ? 8000 : 6000
      });
      return;
    }
    alert(text);
  }

  function cartRemoveErr(err){
    var d = err && err.detail;
    var msg = (d && (d.message || d.error)) || 'Impossible de retirer du panier. Réessayez.';
    sipnToast(msg, 'error');
  }

  function serverAdd(card, onOk, onErr){
    var url = appendAssuranceQs(card.getAttribute('data-pa-add-url'));
    if (!url) { onErr(); return; }
    fetch(url, {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then(function(r){
        return r.json().then(function(d){
          if (!r.ok || !d || !d.ok) {
            var err = new Error((d && d.error) || 'add');
            err.detail = d || {};
            throw err;
          }
          return d;
        });
      })
      .then(function(d){ onOk(d); })
      .catch(function(err){ onErr(err); });
  }

  function serverRemove(paId, onOk, onErr){
    var url = appendAssuranceQs(removeUrlForPaId(paId));
    var tok = getCsrfToken();
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': tok || '',
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: ''
    })
      .then(function(r){
        return r.json().catch(function(){ return {}; }).then(function(d){
          if (!r.ok || !d || !d.ok) {
            var err = new Error((d && d.message) || (d && d.error) || 'remove');
            err.detail = d || {};
            err.status = r.status;
            throw err;
          }
          return d;
        });
      })
      .then(function(d){ onOk(d); })
      .catch(function(err){ onErr(err); });
  }

  function updateStructCartBadges(){
    document.querySelectorAll('.scard-m').forEach(function(struct){
      var rows = struct.querySelectorAll('.scard-m-acte[data-pa-id]');
      var count = 0;
      var total = 0;
      rows.forEach(function(row){
        var id = row.getAttribute('data-pa-id');
        var item = cart.get(id);
        if (item) {
          var quantity = cartQuantity(item);
          count += quantity;
          total += parseFloat(row.getAttribute('data-pa-price') || '0') * quantity;
        }
      });
      struct.classList.toggle('in-cart-struct', count > 0);
      var badge = struct.querySelector('[data-scard-m-cart-badge]');
      if (badge) {
        if (count > 0) {
          badge.hidden = false;
          badge.innerHTML = sipnIconSvg('cart', 'sipn-ico sipn-ico--xs') + ' ' + count + ' · ' + fnum(total) + ' F';
        } else {
          badge.hidden = true;
        }
      }
    });
  }

  function updateCartFloat(){
    var wrap = document.getElementById('cart-float-wrap');
    var cfbCount = document.getElementById('cfb-count');
    var cfbTotal = document.getElementById('cfb-total');
    if (!wrap) return;
    var items = Array.from(cart.values());
    var total = cartTotal(items);
    var itemCount = cartUnits(items);
    if (itemCount) {
      wrap.hidden = false;
      document.body.classList.add('sipn-has-cart-float');
      if (cfbCount) cfbCount.textContent = String(itemCount);
      if (cfbTotal) cfbTotal.textContent = fnum(total) + ' FCFA';
    } else {
      wrap.hidden = true;
      document.body.classList.remove('sipn-has-cart-float');
    }
    if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
  }

  function renderMissingActesBlock(){
    var wrap = document.getElementById('sipn-cart-missing-wrap');
    if (!wrap) return;
    var manquants = getManquants();
    if (!manquants.length) {
      wrap.hidden = true;
      wrap.innerHTML = '';
      return;
    }
    var rows = manquants.map(function(pk){
      var name = getActeName(pk);
      var offers = getOffersForActePk(pk);
      var minPrice = offers.length ? Math.min.apply(null, offers.map(function(o){ return o.price; })) : 0;
      var sub = offers.length
        ? ('dès ' + fnum(minPrice) + ' FCFA · ' + offers.length + ' structure' + (offers.length > 1 ? 's' : ''))
        : 'Voir les structures disponibles';
      return '<div class="cma-row">' +
        '<div><div class="cma-name">' + escapeHtml(name) + '</div>' +
        '<div class="cma-sub">' + escapeHtml(sub) + '</div></div>' +
        '<button type="button" class="cma-cta" data-sipn-goto-results>Choisir →</button></div>';
    }).join('');
    wrap.innerHTML =
      '<div class="cma-card">' +
        '<div class="cma-head">' +
          '<div><div class="cma-title">Actes sans structure assignée</div>' +
          '<div class="cma-sub">Allez dans Résultats pour les assigner</div></div>' +
          '<span class="cma-count">' + manquants.length + '</span>' +
        '</div>' +
        '<div class="cma-body">' + rows + '</div>' +
        '<div class="cma-foot">' +
          '<button type="button" class="cma-foot-btn" data-sipn-goto-results>Voir toutes les structures →</button>' +
        '</div>' +
      '</div>';
    wrap.hidden = false;
  }

  function renderMobilePanierBody(items, total){
    var body = document.getElementById('panier-body-m');
    if (!body || !window.matchMedia('(max-width: 1023px)').matches) return;
    var itemCount = cartUnits(items);
    var countEl = document.querySelector('#cart-mobile-panier .psh-count');
    var clearWrap = document.querySelector('#cart-mobile-panier .panier-section-head form.inline');
    if (countEl) countEl.textContent = String(itemCount);
    if (clearWrap) clearWrap.style.display = items.length ? '' : 'none';

    renderMissingActesBlock();
    var manquants = getManquants();

    if (!items.length && !manquants.length) {
      body.innerHTML =
        '<div class="cart-empty-m">' +
          '<div class="cemi">' + sipnIconSvg('cart', 'sipn-ico sipn-ico--xl') + '</div>' +
          '<div class="cemt">Votre panier est vide.<br>Ajoutez des actes pour construire votre parcours.</div>' +
          '<button type="button" class="cemt-cta" data-sipn-goto-tab="prestations">Rechercher des actes</button>' +
        '</div>';
      return;
    }

    var byOrg = {};
    items.forEach(function(it){
      var key = it.org || 'Structure';
      if (!byOrg[key]) byOrg[key] = [];
      byOrg[key].push(it);
    });
    var orgNames = Object.keys(byOrg);
    var nStructs = orgNames.length;
    var html = '';

    if (!items.length) {
      body.innerHTML = '<div id="sipn-cart-missing-wrap" class="cart-missing-actes-wrap" hidden aria-live="polite"></div>';
      renderMissingActesBlock();
      return;
    }

    orgNames.forEach(function(orgName){
      var orgItems = byOrg[orgName];
      var sub = orgItems.reduce(function(s, it){ return s + it.price * cartQuantity(it); }, 0);
      html += '<div class="panier-struct-group">' +
        '<div class="psg-head">' +
          '<div class="psg-name sipn-ico-inline">' + sipnIconSvg('building', 'sipn-ico sipn-ico--xs') + ' ' + escapeHtml(orgName) + '</div>' +
          '<div class="psg-total">' + fnum(sub) + ' F</div>' +
        '</div>';
      orgItems.forEach(function(it){
        html += '<div class="citem-m">' +
          '<div class="ci-info-m">' +
            '<div class="ci-nom-m">' + escapeHtml(it.acte) + (cartQuantity(it) > 1 ? ' ×' + cartQuantity(it) : '') + '</div>' +
            (it.delai ? '<div class="ci-delai-m sipn-ico-inline">' + sipnIconSvg('clock', 'sipn-ico sipn-ico--xs') + ' ' + escapeHtml(it.delai) + '</div>' : '') +
          '</div>' +
          '<div class="ci-prix-m">' + fnum(it.price * cartQuantity(it)) + ' F</div>' +
          '<button type="button" class="ci-del-m" data-cart-del="' + escapeHtml(it.id) + '" aria-label="Retirer">' + sipnIconSvg('x', 'sipn-ico sipn-ico--sm') + '</button>' +
        '</div>';
      });
      if (cartChariotUrl && orgItems[0].orgId) {
        html += '<div class="psg-foot"><a href="' + cartDevisBaseUrl + '?org=' + encodeURIComponent(orgItems[0].orgId) + '" class="psg-creneau-btn" onclick="return confirm(this.dataset.devisConfirm)" data-devis-confirm="' + escapeHtml(devisConfirmText(orgName, orgItems)) + '">' +
          sipnIconSvg('calendar', 'sipn-ico sipn-ico--sm') + ' Réserver mes actes</a></div>';
      } else if (!cartChariotUrl && !orgItems[0].cartItemId) {
        var orgDevisUrl = cartDevisBaseUrl ? (cartDevisBaseUrl + '?org=' + encodeURIComponent(orgItems[0].orgId)) : cartViewUrl;
        var loginNext = urls.login ? (urls.login + '?next=' + encodeURIComponent(orgDevisUrl)) : ('/accounts/login/?next=' + encodeURIComponent(orgDevisUrl));
        html += '<div class="psg-foot"><a href="' + loginNext + '" class="psg-creneau-btn js-guest-auth-open" data-org-id="' + escapeHtml(orgItems[0].orgId) + '" onclick="return confirm(this.dataset.devisConfirm)" data-devis-confirm="' + escapeHtml(devisConfirmText(orgName, orgItems)) + '">' +
          sipnIconSvg('calendar', 'sipn-ico sipn-ico--sm') + ' Réserver mes actes</a></div>';
      } else {
        html += '<div class="psg-foot"><a href="' + cartViewUrl + '" class="psg-creneau-btn">' +
          sipnIconSvg('cart', 'sipn-ico sipn-ico--sm') + ' Voir le panier</a></div>';
      }
      html += '</div>';
    });

    if (nStructs > 1) {
      html = '<div class="panier-multi-warn"><strong>' + itemCount + ' actes</strong> — une discussion par structure.</div>' + html;
    }

    var infoHtml = '';
    if (cartCoverage && cartCoverage.total_assurance > 0) {
      infoHtml = '<p class="text-[11px] mc-text-accent-dark">Estimation assurance : −' + fnum(cartCoverage.total_assurance) + ' F · estim. patient ' + fnum(cartCoverage.total_patient) + ' F (à confirmer)</p>';
    }

    html += '<div class="panier-total-card">' +
      '<div class="ptc-row">' +
        '<span class="ptc-label">' + itemCount + ' acte' + (itemCount > 1 ? 's' : '') + ' · ' + nStructs + ' structure' + (nStructs > 1 ? 's' : '') + '</span>' +
        '<span class="ptc-value">' + fnum(total) + ' FCFA</span>' +
      '</div>' +
      infoHtml;
    if (cartChariotUrl) {
      html += '<p class="text-[11px] text-gray-500 mt-2">Les actes d’une même structure sont envoyés dans une seule discussion.</p>';
    } else {
      var cartLoginTarget = urls.login ? (urls.login + '?next=' + encodeURIComponent(cartViewUrl)) : ('/accounts/login/?next=' + encodeURIComponent(cartViewUrl));
      html += '<a href="' + cartLoginTarget + '" class="devis-btn-m js-guest-auth-open">' + sipnIconSvg('calendar', 'sipn-ico sipn-ico--sm') + ' Réserver mes actes' +
        (nStructs > 1 ? ' (' + nStructs + ' structures)' : '') + '</a>';
    }
    html += '</div>';

    body.innerHTML = '<div id="sipn-cart-missing-wrap" class="cart-missing-actes-wrap" hidden aria-live="polite"></div>' + html;
    renderMissingActesBlock();

    body.querySelectorAll('[data-cart-del]').forEach(function(btn){
      btn.addEventListener('click', function(){
        var delId = btn.getAttribute('data-cart-del');
        serverRemove(delId, function(d){
          cart.delete(delId);
          cardState(delId);
          applyCartCoverage(d);
          renderCart();
          if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
        }, cartRemoveErr);
      });
    });
  }

  var compVisible = false;
  var compChoices = {};
  var compSort = 'prix';

  function getStructResultsRoot(){
    if (window.matchMedia('(max-width: 1023px)').matches) {
      return document.getElementById('struct-list-m');
    }
    return document.getElementById('struct-list-d');
  }

  function getCompPanelContainer(){
    if (window.matchMedia('(max-width: 1023px)').matches) {
      return document.getElementById('comp-panel-container');
    }
    return document.getElementById('comp-panel-container-d');
  }

  function cartItemFromCard(card, id, serverData){
    var item = {
      id: String(id),
      acte: card.getAttribute('data-pa-acte') || '',
      actePk: String(card.getAttribute('data-pa-acte-pk') || ''),
      org: card.getAttribute('data-pa-org') || '',
      orgId: String(card.getAttribute('data-pa-org-id') || ''),
      delai: card.getAttribute('data-pa-delai') || '',
      price: parseFloat(card.getAttribute('data-pa-price') || '0'),
      quantity: Math.max(1, parseInt(serverData && serverData.quantity, 10) || 1),
      insOk: card.getAttribute('data-pa-ins-match') !== '0',
      cartItemId: null
    };
    if (serverData && serverData.cart_item_id) {
      item.cartItemId = String(serverData.cart_item_id);
    }
    return item;
  }

  function getSelectedActeIds(){
    if (window._sipnGetSelectedIds) {
      var ids = window._sipnGetSelectedIds();
      if (ids && ids.length) return ids.map(String);
    }
    try {
      var stored = JSON.parse(sessionStorage.getItem('sipn_selected_actes') || '[]');
      if (stored.length) return stored.map(String);
    } catch (e) {}
    var u = new URL(window.location.href);
    return u.searchParams.getAll('acte').map(String);
  }

  function getActeName(pk){
    try {
      var names = JSON.parse(sessionStorage.getItem('sipn_acte_names') || '{}');
      if (names[pk]) return names[pk];
    } catch (e) {}
    var root = getStructResultsRoot();
    var row = root
      ? root.querySelector('.scard-m-acte[data-pa-acte-pk="' + pk + '"], .scard-m-acte--ambulance[data-pa-acte-pk="' + pk + '"], .acte-item--ambulance[data-pa-acte-pk="' + pk + '"]')
      : document.querySelector('.scard-m-acte[data-pa-acte-pk="' + pk + '"], .scard-m-acte--ambulance[data-pa-acte-pk="' + pk + '"], .acte-item--ambulance[data-pa-acte-pk="' + pk + '"]');
    if (row) return row.getAttribute('data-pa-acte') || ('Acte #' + pk);
    return 'Acte #' + pk;
  }

  function isAmbulanceActeName(name){
    var low = String(name || '').toLowerCase();
    if (!low) return false;
    return (
      low.indexOf('ambulance') !== -1 ||
      low.indexOf('transport réanimatoire') !== -1 ||
      low.indexOf('transport reanimatoire') !== -1 ||
      low.indexOf('évacuation sanitaire') !== -1 ||
      low.indexOf('evacuation sanitaire') !== -1 ||
      low.indexOf('rapatriement') !== -1 ||
      low.indexOf('couverture') !== -1 ||
      low.indexOf('assistance médicale') !== -1 ||
      low.indexOf('assistance medicale') !== -1
    );
  }

  function ambulanceBtnLabel(name){
    var low = String(name || '').toLowerCase();
    if (low.indexOf('couverture') !== -1 || low.indexOf('événement') !== -1 || low.indexOf('evenement') !== -1 || low.indexOf('assistance') !== -1 || low.indexOf('manifestation') !== -1 || low.indexOf('sportive') !== -1) {
      return '<i class="ti ti-stethoscope"></i> Configurer ma couverture';
    }
    if (low.indexOf('rapatriement') !== -1 || low.indexOf('évacuation') !== -1 || low.indexOf('evacuation') !== -1) {
      return '<i class="ti ti-world"></i> Organiser le rapatriement';
    }
    return '<i class="ti ti-ambulance"></i> Configurer mon trajet';
  }

  function getActePksInCart(){
    var pks = new Set();
    cart.forEach(function(it){
      if (it.actePk) pks.add(String(it.actePk));
    });
    return pks;
  }

  function getCartPaIdForActePk(actePk){
    actePk = String(actePk || '');
    if (!actePk) return null;
    var found = null;
    cart.forEach(function(it, paId){
      if (String(it.actePk) === actePk) found = String(paId);
    });
    return found;
  }

  function isPaBlockedByOtherStructure(paId, actePk){
    actePk = String(actePk || '');
    if (!actePk) return false;
    var inCartPa = getCartPaIdForActePk(actePk);
    return inCartPa !== null && inCartPa !== String(paId);
  }

  function acteConflictMessage(card){
    var actePk = card.getAttribute('data-pa-acte-pk');
    var inCartPa = getCartPaIdForActePk(actePk);
    var otherCard = inCartPa
      ? document.querySelector('.scard[data-pa-id="' + inCartPa + '"], .scard-m-acte[data-pa-id="' + inCartPa + '"]')
      : null;
    var acteName = card.getAttribute('data-pa-acte') || 'Cet acte';
    var orgName = otherCard ? (otherCard.getAttribute('data-pa-org') || 'une autre structure') : 'une autre structure';
    return '« ' + acteName + ' » est déjà dans votre panier chez ' + orgName + '. Retirez-le d\'abord pour le choisir ailleurs.';
  }

  function refreshActeLocks(){
    document.querySelectorAll('.scard-m-acte[data-pa-id], .scard[data-pa-id]').forEach(function(card){
      var paId = card.getAttribute('data-pa-id');
      var actePk = card.getAttribute('data-pa-acte-pk');
      if (!actePk) return;
      var blocked = isPaBlockedByOtherStructure(paId, actePk);
      var inCart = cart.has(String(paId));
      card.classList.toggle('acte-blocked', blocked && !inCart);
      card.setAttribute('aria-disabled', blocked && !inCart ? 'true' : 'false');
      if (blocked && !inCart) {
        card.setAttribute('title', acteConflictMessage(card));
      } else {
        card.removeAttribute('title');
      }
      if (card.classList.contains('scard-m-acte')) {
        var mchk = card.querySelector('.scard-m-checkbox');
        if (mchk) mchk.disabled = blocked && !inCart;
      } else if (card.classList.contains('scard')) {
        var chk = card.querySelector('.ai-check');
        var btn = card.querySelector('.scard-btn-primary');
        if (chk) chk.disabled = blocked && !inCart;
        if (btn) btn.disabled = blocked && !inCart;
      }
    });
  }

  function getManquants(){
    var sel = getSelectedActeIds();
    if (!sel.length) return [];
    var inCart = getActePksInCart();
    return sel.filter(function(pk){
      return !inCart.has(String(pk)) && !isAmbulanceActeName(getActeName(pk));
    });
  }

  function getOffersForActePk(actePk){
    if (isAmbulanceActeName(getActeName(actePk))) return [];
    var root = getStructResultsRoot();
    var rows = root
      ? root.querySelectorAll('.scard-m-acte[data-pa-acte-pk="' + actePk + '"]')
      : document.querySelectorAll('.scard-m-acte[data-pa-acte-pk="' + actePk + '"]');
    return Array.from(rows).map(function(row){
      var cardContainer = row.closest('[data-org-id]');
      var orgId = row.getAttribute('data-pa-org-id') || (cardContainer ? cardContainer.getAttribute('data-org-id') : '');
      return {
        paId: row.getAttribute('data-pa-id'),
        orgId: orgId,
        orgName: row.getAttribute('data-pa-org') || '',
        price: parseFloat(row.getAttribute('data-pa-price') || '0'),
        delai: row.getAttribute('data-pa-delai') || '',
        delaiRank: parseInt(row.getAttribute('data-pa-delai-rank') || '99', 10),
        distanceKm: offerDistanceKm(row),
        insOk: row.getAttribute('data-pa-ins-match') !== '0',
        card: row
      };
    });
  }

  function parseGeoPair(latRaw, lngRaw){
    var lat = parseFloat(latRaw);
    var lng = parseFloat(lngRaw);
    if (!isFinite(lat) || !isFinite(lng)) return null;
    return { lat: lat, lng: lng };
  }

  try {
    var savedGeoEl = document.getElementById('sipn-saved-geo');
    window._sipnSavedGeo = savedGeoEl ? JSON.parse(savedGeoEl.textContent || '{}') : null;
  } catch (e) {
    window._sipnSavedGeo = null;
  }

  function getCompGeoCoords(){
    var latEl = document.getElementById('geo-lat');
    var lngEl = document.getElementById('geo-lng');
    if (latEl && lngEl) {
      var fromForm = parseGeoPair(latEl.value, lngEl.value);
      if (fromForm) return fromForm;
    }
    try {
      var p = new URLSearchParams(window.location.search);
      var fromUrl = parseGeoPair(p.get('lat'), p.get('lng'));
      if (fromUrl) return fromUrl;
    } catch (e) {}
    if (window._sipnSavedGeo) {
      var fromSaved = parseGeoPair(window._sipnSavedGeo.lat, window._sipnSavedGeo.lng);
      if (fromSaved) return fromSaved;
    }
    return null;
  }

  function haversineKm(lat1, lon1, lat2, lon2){
    var R = 6371;
    var dLat = (lat2 - lat1) * Math.PI / 180;
    var dLon = (lon2 - lon1) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function offerDistanceKm(row){
    var raw = row.getAttribute('data-pa-distance-km');
    if (raw) {
      var parsed = parseFloat(raw);
      if (isFinite(parsed)) return parsed;
    }
    var geo = getCompGeoCoords();
    if (!geo) return null;
    var struct = row.closest('.scard-m');
    if (!struct) return null;
    var lat = parseFloat(struct.getAttribute('data-org-lat') || '');
    var lng = parseFloat(struct.getAttribute('data-org-lng') || '');
    if (!isFinite(lat) || !isFinite(lng)) return null;
    return Math.round(haversineKm(geo.lat, geo.lng, lat, lng) * 10) / 10;
  }

  function compOfferTags(offer, rank){
    var tags = [];
    if (rank === 0 && compSort === 'prix') tags.push('<span class="csr-tag csr-tag--cheap"><i class="ti ti-coin"></i> Moins cher</span>');
    if (rank === 0 && compSort === 'proximite' && offer.distanceKm != null) {
      tags.push('<span class="csr-tag csr-tag--dist"><i class="ti ti-map-pin"></i> Plus proche</span>');
    }
    if (rank === 0 && compSort === 'assurance' && offer.insOk) {
      tags.push('<span class="csr-tag csr-tag--ins"><i class="ti ti-shield-check"></i> Couvert</span>');
    }
    if (rank === 0 && compSort === 'delai' && offer.delaiRank <= 4) {
      tags.push('<span class="csr-tag csr-tag--fast"><i class="ti ti-bolt"></i> Plus rapide</span>');
    }
    if (offer.insOk && compSort !== 'assurance') {
      tags.push('<span class="csr-tag csr-tag--ins"><i class="ti ti-shield-check"></i> Couvert</span>');
    }
    if (offer.distanceKm != null && compSort === 'proximite') {
      tags.push('<span class="csr-tag csr-tag--dist"><i class="ti ti-map-pin"></i> ' + offer.distanceKm + ' km</span>');
    } else if (offer.delai && offer.delaiRank <= 4 && compSort !== 'delai') {
      tags.push('<span class="csr-tag csr-tag--fast"><i class="ti ti-clock"></i> ' + escapeHtml(offer.delai) + '</span>');
    }
    return tags.slice(0, 3).join('');
  }

  function sortOffers(offers){
    var list = offers.slice();
    if (compSort === 'proximite') {
      if (!getCompGeoCoords()) {
        list.sort(function(a, b){ return a.price - b.price; });
      } else {
        list.sort(function(a, b){
          var da = a.distanceKm != null ? a.distanceKm : 9999;
          var db = b.distanceKm != null ? b.distanceKm : 9999;
          if (da !== db) return da - db;
          return a.price - b.price;
        });
      }
    } else if (compSort === 'delai') {
      list.sort(function(a, b){
        if (a.delaiRank !== b.delaiRank) return a.delaiRank - b.delaiRank;
        return a.price - b.price;
      });
    } else if (compSort === 'assurance') {
      list.sort(function(a, b){
        if (a.insOk === b.insOk) return a.price - b.price;
        return a.insOk ? -1 : 1;
      });
    } else {
      list.sort(function(a, b){ return a.price - b.price; });
    }
    return list.slice(0, 4);
  }

  function closeCompPanel(){
    compVisible = false;
    ['comp-panel-container', 'comp-panel-container-d'].forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.innerHTML = '';
    });
  }

  function openCompPanel(){
    if (!compVisible && getCompGeoCoords()) {
      var proxH = document.getElementById('geo-proximity');
      if (proxH && proxH.value === '1') compSort = 'proximite';
    }
    compVisible = true;
    renderCompPanel();
    var container = getCompPanelContainer();
    if (container) {
      setTimeout(function(){
        container.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 60);
    }
  }

  function renderCompPanel(){
    var container = getCompPanelContainer();
    if (!container) return;
    var manquants = getManquants();
    if (!manquants.length) {
      container.innerHTML = '';
      return;
    }
    Object.keys(compChoices).forEach(function(pk){
      if (manquants.indexOf(pk) === -1) delete compChoices[pk];
    });

    var sortDefs = [
      { val: 'prix', lbl: '<i class="ti ti-coin"></i> Prix' },
      { val: 'proximite', lbl: '<i class="ti ti-map-pin"></i> Proximité' },
      { val: 'assurance', lbl: '<i class="ti ti-shield-check"></i> Assurance' },
      { val: 'delai', lbl: '<i class="ti ti-bolt"></i> Délai' }
    ];
    var sortBtns = sortDefs.map(function(o){
      return '<button type="button" class="csort-btn' + (compSort === o.val ? ' active' : '') + '" data-comp-sort="' + o.val + '">' + o.lbl + '</button>';
    }).join('');

    var actesHtml = manquants.map(function(actePk){
      var offers = sortOffers(getOffersForActePk(actePk));
      if (!offers.length) return '';
      var chosenId = compChoices[actePk] || null;
      var rowsHtml = offers.map(function(o, idx){
        var isSel = String(chosenId) === String(o.paId);
        var tags = compOfferTags(o, idx);
        var acteNameLow = (getActeName(actePk) || '').toLowerCase();
        var isAmbulanceActe = (
          acteNameLow.includes('ambulance') || 
          acteNameLow.includes('transport') || 
          acteNameLow.includes('rapatriement') || 
          acteNameLow.includes('couverture') || 
          acteNameLow.includes('evacuation') || 
          acteNameLow.includes('évacuation')
        );
        var btnTxt = '<i class="ti ti-ambulance"></i> Configurer mon trajet';
        if (acteNameLow.includes('couverture') || acteNameLow.includes('événement') || acteNameLow.includes('evenement') || acteNameLow.includes('assistance') || acteNameLow.includes('manifestation')) {
          btnTxt = '<i class="ti ti-stethoscope"></i> Configurer ma couverture';
        } else if (acteNameLow.includes('rapatriement') || acteNameLow.includes('évacuation') || acteNameLow.includes('evacuation')) {
          btnTxt = '<i class="ti ti-world"></i> Organiser le rapatriement';
        }
        var trajetBtn = isAmbulanceActe ? '<button type="button" class="csr-trajet-btn" onclick="event.stopPropagation();if(window.openTrajetConfig)window.openTrajetConfig(\'' + escapeHtml(String(o.orgId || '')) + '\', \'' + escapeHtml(actePk) + '\', true)">' + btnTxt + '</button>' : '';
        return '<div class="comp-struct-row' + (isSel ? ' sel' : '') + '" data-comp-acte="' + escapeHtml(actePk) + '" data-comp-pa="' + escapeHtml(o.paId) + '">' +
          '<input type="radio" class="csr-radio" name="comp-' + escapeHtml(actePk) + '"' + (isSel ? ' checked' : '') + ' aria-label="' + escapeHtml(o.orgName) + '">' +
          '<div class="csr-info"><div class="csr-name">' + escapeHtml(o.orgName) + '</div>' +
          (tags ? '<div class="csr-tags">' + tags + '</div>' : '') + '</div>' +
          '<div class="csr-right"><div class="csr-prix">' + fnum(o.price) + ' F</div>' +
          (o.delai ? '<div class="csr-delai"><i class="ti ti-clock"></i> ' + escapeHtml(o.delai) + '</div>' : '') +
          trajetBtn +
          '</div></div>';
      }).join('');
      return '<div class="comp-acte-section"><div class="comp-acte-lbl">' +
        '<div class="cal-dot"></div><div class="cal-name">' + escapeHtml(getActeName(actePk)) + '</div>' +
        '<div class="cal-cnt">' + offers.length + ' option' + (offers.length > 1 ? 's' : '') + '</div></div>' + rowsHtml +
        '<div id="trajet-config-comp-' + actePk + '" class="trajet-config-container hidden"></div></div>';
    }).join('');

    var nbChoix = Object.keys(compChoices).length;
    var totalComp = Object.keys(compChoices).reduce(function(sum, actePk){
      var card = document.querySelector('.scard-m-acte[data-pa-id="' + compChoices[actePk] + '"]');
      return sum + (card ? parseFloat(card.getAttribute('data-pa-price') || '0') : 0);
    }, 0);
    var canTakeAll = manquants.some(function(pk){
      return sortOffers(getOffersForActePk(pk)).length > 0;
    });

    container.innerHTML = '<div class="comp-panel">' +
      '<div class="comp-panel-head"><div class="cph-left">' +
      '<div class="cph-icon" style="font-size:22px;margin-right:8px"><i class="ti ti-bell"></i></div>' +
      '<div><div class="cph-title" style="font-family:\'Syne\',sans-serif;font-size:15px;font-weight:700">Complétez votre devis</div>' +
      '<div class="cph-sub" style="font-size:11.5px;color:#64748b;margin-top:2px">' + manquants.length + ' acte' + (manquants.length > 1 ? 's' : '') + ' non couvert' + (manquants.length > 1 ? 's' : '') + ' par votre sélection</div></div></div>' +
      (canTakeAll ? '<button type="button" class="cph-take-all" data-comp-take-all>Tout prendre</button>' : '') +
      '<button type="button" class="cph-close" data-comp-close aria-label="Fermer"><i class="ti ti-x"></i></button></div>' +
      '<div class="comp-sort-bar">' + sortBtns + '</div>' + actesHtml +
      '<div class="comp-footer"><div class="cf-total">' +
      (nbChoix > 0
        ? '<strong>' + nbChoix + '/' + manquants.length + '</strong> acte' + (nbChoix > 1 ? 's' : '') + ' · <strong>' + fnum(totalComp) + ' FCFA</strong>'
        : 'Choisissez une structure par acte') +
      '</div><button type="button" class="cf-add-btn"' + (nbChoix === 0 ? ' disabled' : '') + ' data-comp-add>Ajouter au panier' +
      (nbChoix > 0 ? ' (' + nbChoix + ')' : '') + '</button></div></div>';
  }

  function toggleCompChoice(actePk, paId){
    actePk = String(actePk);
    paId = String(paId);
    if (compChoices[actePk] === paId) delete compChoices[actePk];
    else compChoices[actePk] = paId;
    renderCompPanel();
  }

  function takeAllCompToCart(){
    var manquants = getManquants();
    var picked = false;
    manquants.forEach(function(actePk){
      var offers = sortOffers(getOffersForActePk(actePk));
      if (!offers.length) return;
      compChoices[String(actePk)] = String(offers[0].paId);
      picked = true;
    });
    if (!picked) return;
    var takeBtn = document.querySelector('[data-comp-take-all]');
    if (takeBtn) takeBtn.disabled = true;
    addCompToCart(function(){
      if (takeBtn) takeBtn.disabled = false;
    });
  }

  function addCompToCart(onDone){
    var entries = Object.entries(compChoices);
    if (!entries.length) return;
    var btn = document.querySelector('[data-comp-add]');
    if (btn) btn.disabled = true;
    var idx = 0;
    function next(){
      if (idx >= entries.length) {
        compChoices = {};
        if (btn) btn.disabled = false;
        checkMissingAfterCartUpdate();
        if (typeof onDone === 'function') onDone();
        return;
      }
      var paId = entries[idx][1];
      idx += 1;
      if (cart.has(paId)) { next(); return; }
      var card = document.querySelector('.scard-m-acte[data-pa-id="' + paId + '"]');
      if (!card) { next(); return; }
      if (isPaBlockedByOtherStructure(paId, card.getAttribute('data-pa-acte-pk'))) {
        sipnToast(acteConflictMessage(card), 'warning');
        next();
        return;
      }
      serverAdd(card, function(d){
        cart.set(paId, cartItemFromCard(card, paId, d));
        cardState(paId);
        renderCart();
        if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
        next();
      }, function(){ next(); });
    }
    next();
  }

  function checkMissingAfterCartUpdate(){
    closeCompPanel();
    updateCartFloat();
  }

  function updateStructCartTotals(){
    document.querySelectorAll('.scard[data-pa-id]').forEach(function(card){
      var orgId = card.getAttribute('data-pa-org-id');
      if (!orgId) return;
      var count = 0;
      var total = 0;
      cart.forEach(function(it){
        if (String(it.orgId) === String(orgId)) {
          var quantity = cartQuantity(it);
          count += quantity;
          total += it.price * quantity;
        }
      });
      var sub = card.querySelector('.scard-total');
      var inner = card.querySelector('.scard-total-text') || card.querySelector('.scard-total-inner');
      if (sub && inner) {
        if (count > 0) {
          inner.textContent = count + ' acte' + (count > 1 ? 's' : '') + ' · ' + fnum(total) + ' F';
          sub.classList.add('visible');
        } else {
          inner.textContent = '';
          sub.classList.remove('visible');
        }
      }
    });
  }

  function cardState(paId){
    paId = String(paId);
    var on = cart.has(paId);
    document.querySelectorAll('[data-pa-id="' + paId + '"]').forEach(function(card){
      if (card.getAttribute('data-ambulance-acte') === '1') return;
      if (card.classList.contains('scard-m-acte')) {
        card.classList.toggle('in-cart-acte', on);
        var mchk = card.querySelector('.scard-m-checkbox');
        if (mchk) mchk.checked = on;
        return;
      }
      if (card.classList.contains('profil-pa-row')) {
        card.classList.toggle('in-cart', on);
        var pchk = card.querySelector('.ai-check');
        if (pchk) pchk.checked = on;
        return;
      }
      if (card.classList.contains('acte-item')) {
        card.classList.toggle('in-cart', on);
        var chk = card.querySelector('.ai-check');
        if (chk) chk.checked = on;
        var scard = card.closest('.scard, .scard-org');
        if (scard) {
          var anyOn = Array.from(scard.querySelectorAll('.acte-item[data-pa-id]')).some(function(r){
            return cart.has(String(r.getAttribute('data-pa-id')));
          });
          scard.classList.toggle('scard--in-cart', anyOn);
        }
        return;
      }
      if (!card.classList.contains('scard')) return;
      var chk = card.querySelector('.ai-check');
      var row = card.querySelector('.acte-item');
      if (chk) chk.checked = on;
      if (row) row.classList.toggle('in-cart', on);
      card.classList.toggle('scard--in-cart', on);
    });
    updateStructCartBadges();
    updateStructCartTotals();
    refreshActeLocks();
    checkMissingAfterCartUpdate();
    updateProfilCartRecap();
  }

  function getProfilDrawerOrgId(){
    var modal = document.getElementById('profil-struct-modal');
    return modal ? (modal.getAttribute('data-org-id') || '') : '';
  }

  function updateProfilCartRecap(){
    var recap = document.getElementById('profil-panier-recap');
    if (!recap) return;
    var orgId = getProfilDrawerOrgId();
    if (!orgId) { recap.innerHTML = ''; return; }
    var items = Array.from(cart.values()).filter(function(it){ return String(it.orgId) === String(orgId); });
    if (!items.length) { recap.innerHTML = ''; return; }
    var itemCount = cartUnits(items);
    var total = cartTotal(items);
    recap.innerHTML =
      '<div class="profil-panier-box">'
      + '<div class="profil-panier-title"><i class="ti ti-shopping-cart"></i> Sélection · ' + itemCount + ' acte' + (itemCount > 1 ? 's' : '') + '</div>'
      + '<div class="profil-panier-cards">'
      + items.map(function(it){
          return '<div class="profil-panier-card">'
            + '<div class="profil-panier-card-name">' + escapeHtml(it.acte) + (cartQuantity(it) > 1 ? ' ×' + cartQuantity(it) : '') + '</div>'
            + '<div class="profil-panier-card-price">' + fnum(it.price * cartQuantity(it)) + ' F</div>'
            + '</div>';
        }).join('')
      + '</div>'
      + '<div class="profil-panier-total-row">'
      + '<div class="profil-panier-total">' + fnum(total) + ' FCFA estimé</div>'
      + '<button type="button" class="profil-panier-clear" data-profil-clear-org="' + escapeHtml(orgId) + '">Vider</button>'
      + '</div></div>';
  }

  function syncProfilDrawerFromCart(){
    var modal = document.getElementById('profil-struct-modal');
    if (!modal || modal.style.display !== 'flex') return;
    modal.querySelectorAll('.profil-pa-row[data-pa-id]').forEach(function(row){
      var id = String(row.getAttribute('data-pa-id'));
      var on = cart.has(id);
      row.classList.toggle('in-cart', on);
      var chk = row.querySelector('.ai-check');
      if (chk) chk.checked = on;
    });
    updateProfilCartRecap();
  }

  function togglePaFromElement(el){
    if (!el) return;
    if (el.getAttribute('data-ambulance-acte') === '1') return;
    var id = String(el.getAttribute('data-pa-id') || '');
    if (!id) return;
    if (cart.has(id)){
      serverRemove(id, function(d){
        cart.delete(id);
        cardState(id);
        applyCartCoverage(d);
        renderCart();
        if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
      }, function(err){
        cartRemoveErr(err);
        cardState(id);
      });
      return;
    }
    if (isPaBlockedByOtherStructure(id, el.getAttribute('data-pa-acte-pk'))) {
      sipnToast(acteConflictMessage(el), 'warning');
      cardState(id);
      return;
    }
    serverAdd(el, function(d){
      cart.set(id, cartItemFromCard(el, id, d));
      cardState(id);
      applyCartCoverage(d);
      renderCart();
      if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
    }, function(err){
      if (err && err.detail && err.detail.error === 'acte_already_in_cart') {
        sipnToast(err.detail.message || acteConflictMessage(el), 'warning');
      } else {
        sipnToast('Impossible d’ajouter au panier. Réessayez.', 'error');
      }
      refreshActeLocks();
      cardState(id);
    });
  }

  function renderCart(){
    var items = Array.from(cart.values());
    var itemCount = cartUnits(items);
    var total = cartTotal(items);
    cartCountEls.forEach(function(el){ el.textContent = String(itemCount); });
    checkMissingAfterCartUpdate();
    var cartFooterEls = document.querySelectorAll('[data-dem-cart-footer]');
    var cartTotalEls = document.querySelectorAll('[data-dem-cart-total]');
    var cartInfoEls = document.querySelectorAll('[data-dem-cart-structs-info]');
    var emptyHtml = '<div class="cart-empty">Cochez des actes dans les structures<br>pour construire votre devis.</div>';
    if (!items.length){
      cartBodyEls.forEach(function(body){ body.innerHTML = emptyHtml; });
      cartFooterEls.forEach(function(footer){ footer.hidden = true; });
      cartCoverage = null;
      renderMobilePanierBody(items, 0);
      return;
    }
    var byOrg = {};
    items.forEach(function(it){
      var key = it.org || 'Structure';
      if (!byOrg[key]) byOrg[key] = [];
      byOrg[key].push(it);
    });
    var orgNames = Object.keys(byOrg);
    var nStructs = orgNames.length;
    var warn = nStructs > 1
      ? '<div class="panier-multi-warn sipn-ico-inline">' + sipnIconSvg('warning', 'sipn-ico sipn-ico--xs') + '<span><strong>' + itemCount + ' actes sélectionnés</strong><br>Une discussion par structure.</span></div>'
      : '';
    var htmlItems = orgNames.map(function(orgName){
      var orgItems = byOrg[orgName];
      var sub = orgItems.reduce(function(s, it){ return s + it.price * cartQuantity(it); }, 0);
      return '<div class="cart-struct-group">'
        + '<div class="csg-head"><span><i class="ti ti-building-hospital"></i> ' + escapeHtml(orgName) + '</span><span class="csg-sub">' + fnum(sub) + ' F</span></div>'
        + orgItems.map(function(it){
          return '<div class="citem' + (it.insOk === false ? ' citem-ins-warn' : '') + '">'
            + '<div class="ci-info"><div class="ci-nom">' + escapeHtml(it.acte) + (cartQuantity(it) > 1 ? ' ×' + cartQuantity(it) : '') + '</div>'
            + (it.delai ? '<div class="ci-struct sipn-ico-inline">' + sipnIconSvg('clock', 'sipn-ico sipn-ico--xs') + ' ' + escapeHtml(it.delai) + '</div>' : '')
            + (it.insOk === false ? '<p class="ci-warn">Structure non listée pour votre mutuelle</p>' : '')
            + '</div><div class="ci-prix">' + fnum(it.price * cartQuantity(it)) + ' F</div>'
            + '<button type="button" class="ci-del" data-cart-del="' + escapeHtml(it.id) + '" aria-label="Retirer">×</button>'
            + '</div>';
        }).join('')
        + '</div>';
    }).join('');
    cartBodyEls.forEach(function(body){
      body.innerHTML = '<div class="cart-items">' + warn + htmlItems + '</div>';
      body.querySelectorAll('[data-cart-del]').forEach(function(btn){
        btn.addEventListener('click', function(){
          var delId = btn.getAttribute('data-cart-del');
          serverRemove(delId, function(d){
            cart.delete(delId);
            cardState(delId);
            applyCartCoverage(d);
            renderCart();
            if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
          }, cartRemoveErr);
        });
      });
    });
    if (cartFooterEls.length) {
      cartFooterEls.forEach(function(cartFooter){ cartFooter.hidden = false; });
      cartTotalEls.forEach(function(el){ el.textContent = fnum(total) + ' FCFA'; });
      var infoHtml = '';
      if (cartCoverage && cartCoverage.total_assurance > 0) {
        infoHtml += '<div class="cart-coverage-est">'
          + '<div class="cart-coverage-est-head sipn-ico-inline">' + sipnIconSvg('shield', 'sipn-ico sipn-ico--xs') + '<span>Couverture estimée</span>'
          + (cartCoverage.insurance_name ? '<span class="cart-coverage-est-ins">' + escapeHtml(cartCoverage.insurance_name) + '</span>' : '')
          + '</div>'
          + '<div class="cart-coverage-est-row">'
          + '<span class="cart-coverage-covered">Pris en charge : <strong>' + fnum(cartCoverage.total_assurance) + ' F</strong></span>'
          + '<span class="cart-coverage-rest">Estimation patient : <strong>' + fnum(cartCoverage.total_patient) + ' F</strong> <small class="text-[10px] text-gray-400 font-normal">(indicatif)</small></span>'
          + '</div></div>';
      }
      if (demAssuranceCtx && demAssuranceCtx.labels && demAssuranceCtx.labels.length) {
        infoHtml += '<div class="cart-ins-filter-note">Filtre assurance : <strong>' + demAssuranceCtx.labels.map(function(l){ return escapeHtml(l); }).join(', ') + '</strong></div>';
      }
      infoHtml += '<span>' + itemCount + ' acte' + (itemCount > 1 ? 's' : '') + ' · ' + nStructs + ' structure' + (nStructs > 1 ? 's' : '') + '</span>';
      cartInfoEls.forEach(function(el){ el.innerHTML = infoHtml; });
    }
    var cartDevisBtn = document.getElementById('dem-cart-devis-btn');
    if (cartDevisBtn) {
      cartDevisBtn.hidden = false;
      if (nStructs === 1 && orgNames.length === 1) {
        var onlyOrgItems = byOrg[orgNames[0]];
        var onlyOrgId = onlyOrgItems && onlyOrgItems[0] && onlyOrgItems[0].orgId;
        cartDevisBtn.setAttribute('data-devis-org-id', onlyOrgId || '');
      } else {
        cartDevisBtn.removeAttribute('data-devis-org-id');
      }
    }
    updateStructCartTotals();
    renderMobilePanierBody(items, total);
    syncProfilDrawerFromCart();
  }

  function hydrateCartFromServer(done){
    var snapshotUrl = urls.cartSnapshotUrl || '/cart/snapshot/';
    fetch(appendAssuranceQs(snapshotUrl), {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
      .then(function(r){
        if (!r.ok) throw new Error('snapshot');
        return r.json();
      })
      .then(function(d){
        if (!d || !d.ok) return;
        applyCartCoverage(d);
        cart.clear();
        (d.items || []).forEach(function(it){
          var id = String(it.id);
          var card = document.querySelector('.scard[data-pa-id="' + id + '"], .scard-m-acte[data-pa-id="' + id + '"], #profil-struct-modal .profil-pa-row[data-pa-id="' + id + '"]');
          cart.set(id, {
            id: id,
            acte: it.acte || (card ? card.getAttribute('data-pa-acte') : '') || '',
            actePk: String(it.acte_pk || (card ? card.getAttribute('data-pa-acte-pk') : '') || ''),
            org: it.org || (card ? card.getAttribute('data-pa-org') : '') || '',
            orgId: it.org_id ? String(it.org_id) : (card ? (card.getAttribute('data-pa-org-id') || '') : ''),
            delai: card ? (card.getAttribute('data-pa-delai') || '') : '',
            price: parseFloat(it.price || (card ? card.getAttribute('data-pa-price') : '0') || '0'),
            quantity: Math.max(1, parseInt(it.qty, 10) || 1),
            insOk: card ? card.getAttribute('data-pa-ins-match') !== '0' : it.insOk !== false,
            cartItemId: it.cart_item_id || null
          });
        });
        cart.forEach(function(_, id){ cardState(id); });
        refreshActeLocks();
        renderCart();
        if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
        checkMissingAfterCartUpdate();
      })
      .catch(function(){})
      .finally(function(){ if (typeof done === 'function') done(); });
  }

  function toggleCartFromCard(card){
    var id = String(card.getAttribute('data-pa-id') || '');
    if (!id) return;
    if (cart.has(id)){
      serverRemove(id, function(d){
        cart.delete(id);
        cardState(id);
        applyCartCoverage(d);
        renderCart();
        if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
      }, function(err){
        cartRemoveErr(err);
        cardState(id);
      });
    } else {
      if (isPaBlockedByOtherStructure(id, card.getAttribute('data-pa-acte-pk'))) {
        sipnToast(acteConflictMessage(card), 'warning');
        cardState(id);
        return;
      }
      serverAdd(card, function(d){
        cart.set(id, cartItemFromCard(card, id, d));
        cardState(id);
        applyCartCoverage(d);
        renderCart();
        if (typeof d.cart_count !== 'undefined') syncCartBadges(d.cart_count);
      }, function(err){
        if (err && err.detail && err.detail.error === 'acte_already_in_cart') {
          sipnToast(err.detail.message || acteConflictMessage(card), 'warning');
        } else {
          sipnToast('Impossible d’ajouter au panier. Réessayez ou ouvrez la fiche offre.', 'error');
        }
        refreshActeLocks();
        cardState(id);
      });
    }
  }

  function syncAllCartCardStates(){
    document.querySelectorAll('.scard[data-pa-id], .scard-m-acte[data-pa-id], .acte-item[data-pa-id]').forEach(function(card){
      var id = card.getAttribute('data-pa-id');
      if (id) cardState(id);
    });
  }

  function initCartCardDelegation(){
    var root = document.getElementById('layout-body');
    if (!root || root.getAttribute('data-sipn-cart-delegation') === '1') return;
    root.setAttribute('data-sipn-cart-delegation', '1');
    root.addEventListener('click', function(e){
      var t = e.target;
      if (!t || !t.closest) return;
      if (t.closest('.profil-drawer-trigger, .scard-m-profile-btn, .scard-btn-trajet, .scard-btn-secondary, .org-preview-trigger, .scm-cta, [data-sipn-open-comp-panel], .scard-btn-trajet--inline')) return;
      var card = t.closest('.scard-m-acte[data-pa-id], .scard[data-pa-id], .acte-item[data-pa-id]');
      if (!card || card.getAttribute('data-ambulance-acte') === '1') return;
      if (card.closest('.scard--unverified, .scard-m--unverified') || card.getAttribute('data-pa-unverified') === '1' || card.getAttribute('data-org-unverified') === '1') {
        t.checked = false;
        e.preventDefault();
        sipnToast("Cette structure est en attente d'approbation et ne peut pas encore être sélectionnée.", 'warning');
        return;
      }
      if (t.closest('.scard-m-checkbox, .ai-check')) return;
      var paId = card.getAttribute('data-pa-id');
      if (isPaBlockedByOtherStructure(paId, card.getAttribute('data-pa-acte-pk')) && !cart.has(String(paId))) {
        e.preventDefault();
        sipnToast(acteConflictMessage(card), 'warning');
        return;
      }
      e.preventDefault();
      toggleCartFromCard(card);
    });
    root.addEventListener('change', function(e){
      var t = e.target;
      if (!t || (!t.classList.contains('scard-m-checkbox') && !t.classList.contains('ai-check'))) return;
      var card = t.closest('.scard-m-acte[data-pa-id], .scard[data-pa-id], .acte-item[data-pa-id]');
      if (!card || card.getAttribute('data-ambulance-acte') === '1') return;
      if (card.closest('.scard--unverified, .scard-m--unverified') || card.getAttribute('data-pa-unverified') === '1' || card.getAttribute('data-org-unverified') === '1') {
        t.checked = false;
        e.preventDefault();
        sipnToast("Cette structure est en attente d'approbation et ne peut pas encore être sélectionnée.", 'warning');
        return;
      }
      var paId = card.getAttribute('data-pa-id');
      if (isPaBlockedByOtherStructure(paId, card.getAttribute('data-pa-acte-pk')) && !cart.has(String(paId))) {
        t.checked = false;
        sipnToast(acteConflictMessage(card), 'warning');
        return;
      }
      e.stopPropagation();
      toggleCartFromCard(card);
    });
  }

  initCartCardDelegation();
  syncAllCartCardStates();
  if (typeof getManquants === 'function' && getManquants().length > 0) {
    compVisible = true;
    renderCompPanel();
  }
  document.addEventListener('click', function(e){
    var btnAll = e.target && e.target.closest ? e.target.closest('[data-scard-add-all]') : null;
    if (btnAll) {
      e.preventDefault();
      var orgId = btnAll.getAttribute('data-scard-add-all');
      var card = document.getElementById('sm-' + orgId);
      if (card) {
        var checkboxes = card.querySelectorAll('.scard-m-checkbox');
        checkboxes.forEach(function(cb){
          if (!cb.checked) {
            cb.checked = true;
            var row = cb.closest('.scard-m-acte');
            if (row) toggleCartFromCard(row);
          }
        });
      }
      return;
    }
    var btn = e.target && e.target.closest ? e.target.closest('#dem-cart-clear-btn, #btn-vider-panier, .psh-clear, .profil-panier-clear') : null;
    if (!btn) return;
    var csrfToken = getCsrfToken();
    var clearForm = btn.closest ? btn.closest('form') : null;
    var actionUrl = (clearForm && clearForm.action) ? clearForm.action : '/cart/clear/';

    function resetCartUI(){
      cart.clear();
      renderCart();
      syncCartBadges(0);
      syncAllCartCardStates();
      var pBody = document.getElementById('panier-body-m');
      if (pBody) {
        pBody.innerHTML = '<div class="cart-empty-m"><div class="cemi"><i class="ti ti-shopping-cart"></i></div><div class="cemt">Votre panier est vide.<br>Ajoutez des actes pour construire votre parcours.</div><button type="button" class="cemt-cta" data-sipn-goto-tab="prestations">Rechercher des actes</button></div>';
      }
      var pHeadCount = document.querySelector('.psh-count');
      if (pHeadCount) pHeadCount.textContent = '0';
      if (typeof renderCompPanel === 'function') renderCompPanel();
      if (typeof sipnToast === 'function') sipnToast('Panier vidé', 'info');
      _refreshChariotPanel();
    }

    function _refreshChariotPanel(){
      var chariotPanel = document.querySelector('.pac-chariot-desktop');
      if (!chariotPanel) return;
      fetch('/users/compte/panel/chariot/?pac_partial=1', {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-MedCare-PAC': '1' }
      }).then(function(r){ return r.ok ? r.text() : null; })
        .then(function(html){
          if (!html) return;
          var tmp = document.createElement('div');
          tmp.innerHTML = html;
          var fresh = tmp.querySelector('.pac-chariot-desktop');
          if (fresh) chariotPanel.replaceWith(fresh);
        }).catch(function(){});
    }

    fetch(actionUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest'
      }
    }).then(function(r){
      if (r.ok) { resetCartUI(); return; }
      return fetch('/cart/guest/clear/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' }
      }).then(function(r2){ if (r2.ok) resetCartUI(); });
    }).catch(function(){
      fetch('/cart/guest/clear/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' }
      }).then(function(r2){ if (r2.ok) resetCartUI(); }).catch(resetCartUI);
    });
  });

  var cartFloatBtn = document.getElementById('sipn-cart-float-btn');
  function goToPanierFromResults(){
    if (!cart.size) return;
    if (window._sipnGoPanierTab) window._sipnGoPanierTab();
  }
  if (cartFloatBtn) {
    cartFloatBtn.addEventListener('click', function(e){
      e.preventDefault();
      goToPanierFromResults();
    });
  }

  document.addEventListener('click', function(ev){
    var t = ev.target;
    if (!t || !t.closest) return;
    if (t.closest('[data-sipn-open-comp-panel]')) {
      ev.preventDefault();
      openCompPanel();
      return;
    }
    var sortBtn = t.closest('[data-comp-sort]');
    if (sortBtn) {
      var newSort = sortBtn.getAttribute('data-comp-sort') || 'prix';
      if (newSort === 'proximite' && !getCompGeoCoords()) {
        compSort = 'proximite';
        renderCompPanel();
        if (typeof window._sipnOpenGeo === 'function') {
          window._sipnOpenGeo();
          sipnToast('Indiquez votre position pour trier par proximité.', 'info');
        } else {
          sipnToast('Indiquez votre position pour trier par proximité.', 'warning');
        }
        return;
      }
      compSort = newSort;
      renderCompPanel();
      return;
    }
    if (t.closest('[data-comp-close]')) {
      closeCompPanel();
      return;
    }
    if (t.closest('[data-comp-add]')) {
      addCompToCart();
      return;
    }
    if (t.closest('[data-comp-take-all]')) {
      takeAllCompToCart();
      return;
    }
    var row = t.closest('[data-comp-acte][data-comp-pa]');
    if (row) {
      if (t.closest('.csr-trajet-btn')) return;
      var actePk = row.getAttribute('data-comp-acte');
      if (isAmbulanceActeName(getActeName(actePk))) return;
      toggleCompChoice(actePk, row.getAttribute('data-comp-pa'));
    }
  });

  document.addEventListener('click', function(ev){
    var t = ev.target;
    if (!t || !t.closest) return;
    if (t.closest('.scard-btn-trajet')) return;
    var ambRow = t.closest('.acte-item--ambulance, .scard-m-acte--ambulance');
    if (!ambRow) return;
    ev.preventDefault();
    var orgId = ambRow.getAttribute('data-pa-org-id');
    var acte = ambRow.getAttribute('data-pa-acte');
    if (orgId && window.openTrajetConfig) {
      window.openTrajetConfig(orgId, acte);
    }
  });

  window._sipnIsAmbulanceActeName = isAmbulanceActeName;
  window._sipnAmbulanceBtnLabel = ambulanceBtnLabel;
  window._sipnGetDevisConfirmTextForOrg = function(orgId){
    var items = Array.from(cart.values()).filter(function(item){
      return String(item.orgId) === String(orgId);
    });
    return items.length ? devisConfirmText(items[0].org || 'cette structure', items) : '';
  };

  hydrateCartFromServer(function(){
    checkMissingAfterCartUpdate();
  });
  window._sipnHydrateCart = hydrateCartFromServer;
  window._sipnSyncCartCardStates = syncAllCartCardStates;
  window._sipnGetCartCount = function(){ return cartUnits(Array.from(cart.values())); };
  window._sipnRenderCart = renderCart;
  window._sipnOpenCompPanel = openCompPanel;
  window._sipnCheckMissingCart = checkMissingAfterCartUpdate;
  window._sipnTogglePaFromElement = togglePaFromElement;
  window._sipnSyncProfilDrawer = syncProfilDrawerFromCart;
  window._sipnUpdateProfilCartRecap = updateProfilCartRecap;

  window.addEventListener('resize', function(){
    if (!compVisible) return;
    renderCompPanel();
  });
})();

