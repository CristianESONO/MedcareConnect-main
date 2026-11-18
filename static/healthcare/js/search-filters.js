/**
 * MedCare - Search Filters & Core Interactivity
 * Gère les filtres de recherche desktop et formulaires :
 * - Select2 & puces déroulantes
 * - Slider de budget / prix
 * - Soumission automatique avec debounce
 * - Autocomplétion recherche libre (#search-q)
 * - Navigation par piliers & lots prédéfinis
 * - Chips filtres actifs
 */
(function(){
  'use strict';

  var cfg = window.SIPN_CONFIG || {};
  var urls = cfg.urls || {};
  var pricing = cfg.pricingSlider || {};
  var PMIN = (pricing.pmin !== undefined) ? pricing.pmin : 0;
  var PMAX = (pricing.pmax !== undefined) ? pricing.pmax : 500000;
  var curMin = (pricing.curMin !== undefined && pricing.curMin !== 0) ? pricing.curMin : PMIN;
  var curMax = (pricing.curMax !== undefined && pricing.curMax !== 0) ? pricing.curMax : PMAX;

  var searchUrl = urls.search || '/recherche/';
  var autocompleteUrl = urls.autocomplete || '/api/search/autocomplete/';
  var budgetApiUrl = urls.actesBudget || '/api/actes/budget/';
  var bundleSaveUrl = urls.bundleSaveSession || '/bundle/save-session/';

  function getCookie(name){
    return window.SIPNUtils ? window.SIPNUtils.getCookie(name) : '';
  }
  function getCsrfToken(){
    return window.SIPNUtils ? window.SIPNUtils.getCsrfToken() : '';
  }
  function $(s, p){ return (p || document).querySelector(s); }
  function $$(s, p){ return Array.prototype.slice.call((p || document).querySelectorAll(s)); }

  /* ─── Select2 ──────────────────────────────────────────────────── */
  if (window.jQuery) {
    jQuery(function($){
      $('.s2-single, .s2-single-mob').select2({placeholder:'— choisir —', allowClear:true, width:'100%'});
      $('.s2-multi, .s2-multi-mob').not('.s2-multi-dem-bar').select2({placeholder:'Sélectionner…', allowClear:true, width:'100%', closeOnSelect:false});
      var $form = $('#search-form');
      if ($form.length) {
        var s2t = null;
        $('.s2-multi, .s2-multi-mob').not('.s2-multi-dem-bar').on('select2:select select2:unselect select2:clear', function(){
          if (window.__suppressAutoFilterSubmit) return;
          clearTimeout(s2t);
          s2t = setTimeout(function(){ $form[0].submit(); }, 400);
        });
      }
    });
  }

  /* ─── Filtre local « Parcourir les actes » (piliers Déméthior) ─── */
  function filterActeTree(inp, tree) {
    if (window.SIPNUtils && window.SIPNUtils.filterActeTree) {
      window.SIPNUtils.filterActeTree(inp, tree);
      return;
    }
    if (!inp || !tree) return;
    inp.addEventListener('input', function(){
      var q = (inp.value || '').trim().toLowerCase();
      tree.querySelectorAll('[data-dem-acte-group]').forEach(function(grp){
        var rows = grp.querySelectorAll('[data-dem-acte-name]');
        var nvis = 0;
        rows.forEach(function(row){
          var nm = row.getAttribute('data-dem-acte-name') || '';
          var show = !q || nm.indexOf(q) !== -1;
          row.style.display = show ? '' : 'none';
          if (show) nvis++;
        });
        var vis = (!q || nvis > 0);
        grp.style.display = vis ? '' : 'none';
        if (vis && q && nvis > 0 && grp.tagName === 'DETAILS') grp.open = true;
      });
    });
  }

  /* Connexion filtre -> arbre pour le mode embed no-wrap (sidebar desktop démo) */
  (function(){
    var navInp = document.getElementById('nav-search-input');
    var navTree = document.getElementById('nav-tree');
    if (navInp && navTree) filterActeTree(navInp, navTree);
  })();

  /* Connexion filtre -> arbre pour les modes classiques (.dem-acte-browse) */
  $$('.dem-acte-browse').forEach(function(browse){
    var inp = browse.querySelector('.dem-acte-filter-input');
    var tree = browse.querySelector('.dem-acte-tree');
    filterActeTree(inp, tree);
  });

  /* ─── Multi-sélection dans « Parcourir les actes » ──────────────── */
  (function initDesktopActeMultiSelect(){
    if (!document.body.classList.contains('sipn-prestations')) return;
    function navigateActePool(ids){
      var u = new URL(window.location.href);
      u.searchParams.delete('acte');
      u.searchParams.delete('lot');
      u.searchParams.delete('page');
      ids.forEach(function(id){ u.searchParams.append('acte', String(id)); });
      if (ids.length) u.hash = 'results-col';
      else u.hash = '';
      var targetUrl = u.toString();
      if (typeof window.updatePageContent === 'function') {
        history.pushState({}, '', targetUrl);
        window.updatePageContent(targetUrl);
      } else {
        var waitStart = Date.now();
        var poller = setInterval(function(){
          if (typeof window.updatePageContent === 'function') {
            clearInterval(poller);
            history.pushState({}, '', targetUrl);
            window.updatePageContent(targetUrl);
          } else if (Date.now() - waitStart > 3000) {
            clearInterval(poller);
            window.location.assign(targetUrl);
          }
        }, 50);
      }
    }

    var _clickLock = false;
    document.addEventListener('click', function(e){
      var row = e.target.closest('.dem-acte-row--multi');
      if (!row) return;
      
      e.preventDefault();
      e.stopPropagation();

      if (_clickLock) return;
      _clickLock = true;
      setTimeout(function(){ _clickLock = false; }, 150);

      var pk = row.getAttribute('data-dem-acte-pk');
      if (!pk) return;
      var name = row.getAttribute('data-dem-acte-name') || row.innerText.trim();

      var sf = document.getElementById('search-form');
      var ids = sf
        ? Array.from(sf.querySelectorAll('input[name="acte"]')).map(function(inp){ return String(inp.value); })
        : (new URL(window.location.href)).searchParams.getAll('acte');

      var idx = ids.indexOf(String(pk));
      var isNowActive = (idx === -1);
      if (isNowActive) {
        ids.push(String(pk));
      } else {
        ids.splice(idx, 1);
      }

      document.querySelectorAll('.dem-acte-row--multi[data-dem-acte-pk="' + pk + '"]').forEach(function(r){
        r.classList.toggle('active', isNowActive);
        var c = r.querySelector('.dem-acte-chk');
        if (c) c.checked = isNowActive;
      });

      if (sf) {
        sf.querySelectorAll('input[name="acte"]').forEach(function(inp){ inp.remove(); });
        ids.forEach(function(id){
          var h = document.createElement('input');
          h.type = 'hidden';
          h.name = 'acte';
          h.value = id;
          sf.appendChild(h);
        });
      }

      if (isNowActive) {
        if (window._sipnAddSelectedActe) window._sipnAddSelectedActe(pk, name);
      } else {
        if (window._sipnRemoveSelectedActe) window._sipnRemoveSelectedActe(pk);
      }

      if (window.matchMedia('(min-width: 1024px)').matches) {
        clearTimeout(window.__desktopActeNavT);
        window.__desktopActeNavT = setTimeout(function() {
          var sfCur = document.getElementById('search-form');
          var curIds = sfCur
            ? Array.from(sfCur.querySelectorAll('input[name="acte"]')).map(function(i){ return i.value; })
            : ids.slice();
          navigateActePool(curIds);
        }, 350);
      } else {
        if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
      }
    });
  })();

  /* Desktop : après choix d'une famille, amener l'arbre actes dans le viewport */
  (function(){
    if (!document.body.classList.contains('sipn-prestations')) return;
    function scrollToActesSidebar(){
      if (!window.matchMedia('(min-width: 1024px)').matches) return;
      var sidebar = document.getElementById('sidebar-desktop');
      if (!sidebar) return;
      var y = sidebar.getBoundingClientRect().top + window.pageYOffset - 16;
      window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
      var fam = sidebar.querySelector('.dem-acte-family');
      if (fam && fam.tagName === 'DETAILS') fam.open = true;
    }
    if (window.location.hash === '#sidebar-desktop') {
      window.requestAnimationFrame(scrollToActesSidebar);
    }
  })();

  /* ─── Slider de prix (desktop + mobile) ────────────────────────── */
  function fmtPrice(v){ return Math.round(v).toLocaleString('fr-FR'); }
  function initSlider(elId, lblMinId, lblMaxId, inpMinId, inpMaxId){
    if (typeof noUiSlider === 'undefined') return;
    var el = document.getElementById(elId);
    if (!el || el.noUiSlider) return;
    var lblMin = document.getElementById(lblMinId), lblMax = document.getElementById(lblMaxId);
    var inpMin = document.getElementById(inpMinId), inpMax = document.getElementById(inpMaxId);
    noUiSlider.create(el, {
      start: [curMin, curMax],
      connect: true,
      step: 500,
      range: { min: PMIN, max: PMAX },
      tooltips: [{ to: fmtPrice }, { to: fmtPrice }]
    });
    el.noUiSlider.on('update', function(vals){
      var lo = Math.round(vals[0]), hi = Math.round(vals[1]);
      if (lblMin) lblMin.textContent = fmtPrice(lo);
      if (lblMax) lblMax.textContent = fmtPrice(hi);
      if (inpMin) inpMin.value = (lo <= PMIN) ? '' : lo;
      if (inpMax) inpMax.value = (hi >= PMAX) ? '' : hi;
    });
  }
  initSlider('price-slider','price-label-min','price-label-max','inp-price-min','inp-price-max');
  initSlider('price-slider-mob','price-label-min-mob','price-label-max-mob','inp-price-min-mob','inp-price-max-mob');
  function wireSliderAutoSubmit(elId){
    var el = document.getElementById(elId);
    var sf = document.getElementById('search-form');
    if (!el || !el.noUiSlider || !sf) return;
    el.noUiSlider.on('end', function(){ sf.submit(); });
  }
  wireSliderAutoSubmit('price-slider');
  wireSliderAutoSubmit('price-slider-mob');

  /* ─── Filtres : envoi auto du formulaire (sans bouton Appliquer) ─ */
  (function(){
    var form = document.getElementById('search-form');
    if (!form) return;
    var debT = null;
    function schedSubmit(){
      clearTimeout(debT);
      debT = setTimeout(function(){ form.submit(); }, 380);
    }
    form.addEventListener('change', function(e){
      if (window.__suppressAutoFilterSubmit) return;
      var el = e.target;
      if (!el || !el.name) return;
      if (el.tagName === 'SELECT') {
        if (el.classList.contains('s2-multi') || el.classList.contains('s2-multi-mob') || el.classList.contains('s2-multi-dem-bar')) return;
        if (el.multiple && !el.classList.contains('select2-hidden-accessible')) { schedSubmit(); return; }
        form.submit();
        return;
      }
      if (el.tagName === 'INPUT' && el.type === 'checkbox' && el.name === 'domicile') form.submit();
    });
  })();

  /* ─── Mobile prestations : navigation vers résultats après recherche acte ─ */
  function hcIsMobilePrestations(){
    return window.matchMedia('(max-width: 1023px)').matches
      && document.body.classList.contains('sipn-prestations');
  }
  function hcBuildActeResultsUrl(acteId){
    var u = new URL(searchUrl, window.location.origin);
    var formEl = document.getElementById('search-form');
    if (formEl) {
      var fd = new FormData(formEl);
      fd.delete('acte');
      fd.delete('page');
      fd.forEach(function(v, k){
        if (v !== '' && v != null) u.searchParams.append(k, v);
      });
    } else {
      (new URLSearchParams(window.location.search)).forEach(function(v, k){
        if (k !== 'acte' && k !== 'page') u.searchParams.append(k, v);
      });
    }
    u.searchParams.set('acte', String(acteId));
    if (!u.searchParams.get('sort')) u.searchParams.set('sort', 'price_asc');
    u.hash = 'results-col';
    return u.toString();
  }
  function hcGoActeResults(acteId){
    window.location.href = hcBuildActeResultsUrl(acteId);
  }
  function hcSearchUrlImpliesResults(){
    var sp = new URLSearchParams(window.location.search);
    return window.location.hash === '#results-col'
      || /[?&]acte=/.test(window.location.search)
      || ((sp.get('q') || '').trim().length >= 2);
  }
  window.hcIsMobilePrestations = hcIsMobilePrestations;
  window.hcBuildActeResultsUrl = hcBuildActeResultsUrl;
  window.hcGoActeResults = hcGoActeResults;
  window.hcSearchUrlImpliesResults = hcSearchUrlImpliesResults;

  /* ─── Autocomplete recherche libre (#search-q) ─ */
  function initHealthcareSearchAutocomplete(){
    if (document.body.classList.contains('sipn-prestations')) {
      var zone = document.getElementById('search-input-zone');
      var mode = zone ? zone.getAttribute('data-dem-mode') : null;
      if (!mode || mode === 'acte') return;
    }
    var input = document.getElementById('search-q'), list = document.getElementById('ac-list'),
        formEl = document.getElementById('search-form');
    if (!input || !list || !formEl) return;
    if (window.__hcAcController) try { window.__hcAcController.abort(); } catch (e) {}
    window.__hcAcController = new AbortController();
    var sig = window.__hcAcController.signal;
    var acURL = autocompleteUrl;
    var typeLabels = {famille:'Familles de soins', acte:'Examens & actes', centre:'Centres de santé'};
    var typeIcons  = {famille:'<i class="ti ti-building-hospital"></i>', acte:'<i class="ti ti-flask"></i>', centre:'<i class="ti ti-map-pin"></i>'};
    var timer = null, activeIdx = -1, items = [];
    function highlight(text, q){
      if (!q) return text;
      var re = new RegExp('('+q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi');
      return text.replace(re, '<span class="ac-highlight">$1</span>');
    }
    function render(data, q){
      list.innerHTML = ''; items = []; activeIdx = -1;
      if (!data.length){ list.style.display='none'; return; }
      var grouped = {};
      data.forEach(function(s){ (grouped[s.type] = grouped[s.type] || []).push(s); });
      ['famille','acte','centre'].forEach(function(type){
        var arr = grouped[type]; if (!arr) return;
        var g = document.createElement('div'); g.className='ac-group'; g.textContent=typeLabels[type];
        list.appendChild(g);
        arr.forEach(function(s){
          var el = document.createElement('div'); el.className='ac-item';
          el.innerHTML = '<span class="ac-icon t-'+type+'">'+typeIcons[type]+'</span>' +
            '<span class="min-w-0 truncate">' + highlight(s.label, q) + '</span>' +
            (s.detail ? '<span class="ac-detail">'+s.detail+'</span>' : '');
          el.addEventListener('mousedown', function(e){
            e.preventDefault();
            list.style.display = 'none';
            input.value = s.label;
            if (s.id) {
              var cb = document.querySelector('input[name="acte"][value="' + s.id + '"]');
              if (cb && !cb.checked) {
                cb.checked = true;
                cb.dispatchEvent(new Event('change', { bubbles: true }));
              }
            }
            input.focus();
          });
          list.appendChild(el); items.push(el);
        });
      });
      list.style.display='block';
    }
    function clearAC(){ list.style.display='none'; list.innerHTML=''; items=[]; activeIdx=-1; }
    function setActive(idx){
      items.forEach(function(el){ el.classList.remove('ac-active'); });
      if (idx>=0 && idx<items.length){ items[idx].classList.add('ac-active'); activeIdx=idx; items[idx].scrollIntoView({block:'nearest'}); }
      else activeIdx = -1;
    }
    input.addEventListener('input', function(){
      var q = input.value.trim();
      clearTimeout(timer);
      if (q.length < 2){ clearAC(); return; }
      timer = setTimeout(function(){
        fetch(acURL + '?q=' + encodeURIComponent(q))
          .then(function(r){ return r.json(); })
          .then(function(d){ render(d.suggestions || [], q); })
          .catch(clearAC);
      }, 220);
    }, { signal: sig });
    input.addEventListener('keydown', function(e){
      if (list.style.display==='none' || !items.length) return;
      if (e.key==='ArrowDown'){ e.preventDefault(); setActive(activeIdx<items.length-1?activeIdx+1:0); }
      else if (e.key==='ArrowUp'){ e.preventDefault(); setActive(activeIdx>0?activeIdx-1:items.length-1); }
      else if (e.key==='Enter' && activeIdx>=0){ e.preventDefault(); items[activeIdx].dispatchEvent(new MouseEvent('mousedown')); }
      else if (e.key==='Escape') clearAC();
    }, { signal: sig });
    input.addEventListener('focus', function(){ if (input.value.trim().length>=2) input.dispatchEvent(new Event('input')); }, { signal: sig });
    document.addEventListener('click', function(e){
      if (!input.contains(e.target) && !list.contains(e.target)) clearAC();
    }, { signal: sig });
  }
  window.initHealthcareSearchAutocomplete = initHealthcareSearchAutocomplete;

  /* ─── « Je cherche par » : modes & dropdowns ────────────────────── */
  (function initDemSearchModes(){
    var form = document.getElementById('search-form');
    if (!form) return;
    var demActeSearchInnerHTML = '';
    var savedSearchQ = '';
    function demHideQuickResults(){
      var qr = document.getElementById('quick-results');
      if (qr) { qr.classList.add('hidden'); qr.innerHTML = ''; }
    }
    function demFmtF(v){ return Math.round(Number(v)).toLocaleString('fr-FR'); }
    function demEscapeAttr(s){
      if (s == null || s === '') return '';
      return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
    }
    function demDelaiMaster(){ return form.querySelector('select[name="delai"]'); }
    function demAssuranceCenter(){ return document.getElementById('id-assurance-dem-center'); }
    function demEnableAssuranceCenter(){
      var center = demAssuranceCenter();
      if (!center) return;
      center.disabled = false;
    }
    function demEnableDelaiMaster(){
      var m = demDelaiMaster();
      if (m) m.disabled = false;
    }
    function demEnableCityInputs(){
      ['city-input-desk','city-quick'].forEach(function(id){
        var el = document.getElementById(id);
        if (el) el.disabled = false;
      });
    }
    function demSyncFromBarsBeforeActe(){
      window.__suppressAutoFilterSubmit = true;
      var bDel = document.getElementById('dem-bar-delai');
      var m = demDelaiMaster();
      if (bDel && m) m.value = bDel.value;
      demEnableDelaiMaster();
      var bCity = document.getElementById('dem-bar-city');
      var cDesk = document.getElementById('city-input-desk');
      var cQuick = document.getElementById('city-quick');
      if (bCity) {
        if (cDesk) cDesk.value = bCity.value;
        if (cQuick) cQuick.value = bCity.value;
      }
      demEnableCityInputs();
      var bAss = document.getElementById('dem-bar-assurance');
      var center = demAssuranceCenter();
      if (bAss && center) {
        demEnableAssuranceCenter();
        var vals;
        if (window.jQuery && jQuery(bAss).data('select2')) {
          vals = jQuery(bAss).val() || [];
          if (!Array.isArray(vals)) vals = vals ? [vals] : [];
          try { jQuery(bAss).select2('destroy'); } catch (e) {}
        } else {
          vals = Array.from(bAss.selectedOptions).map(function(o){ return o.value; });
        }
        if (window.jQuery) jQuery(center).val(vals).trigger('change');
        else Array.from(center.options).forEach(function(o){ o.selected = vals.indexOf(o.value) !== -1; });
      } else if (center) {
        demEnableAssuranceCenter();
      }
      setTimeout(function(){ window.__suppressAutoFilterSubmit = false; }, 180);
    }
    if (!form.getAttribute('data-dem-delai-sync')) {
      form.setAttribute('data-dem-delai-sync', '1');
      form.addEventListener('submit', function(){
        var bDel = document.getElementById('dem-bar-delai');
        var m = demDelaiMaster();
        if (bDel && m) {
          m.value = bDel.value;
          m.disabled = false;
        }
      }, true);
    }
    if (!form.getAttribute('data-dem-assurance-hidden-sync')) {
      form.setAttribute('data-dem-assurance-hidden-sync', '1');
      form.addEventListener('submit', function(){
        var zone = document.getElementById('search-input-zone');
        if (!zone || zone.getAttribute('data-dem-mode') !== 'assurance') return;
        var bar = document.getElementById('dem-bar-assurance');
        if (!bar) return;
        form.querySelectorAll('input.dem-bar-assurance-hidden').forEach(function(n){ n.remove(); });
        Array.from(bar.selectedOptions).forEach(function(opt){
          var h = document.createElement('input');
          h.type = 'hidden'; h.name = 'assurance'; h.value = opt.value; h.className = 'dem-bar-assurance-hidden';
          form.appendChild(h);
        });
      }, true);
    }
    function setModeActive(mode){
      form.querySelectorAll('.search-modes [data-dem-search-mode]').forEach(function(el){
        var m = el.getAttribute('data-dem-search-mode');
        if (!m) return;
        var on = (m === mode);
        el.classList.toggle('active', on);
        if (on) el.setAttribute('aria-current', 'page');
        else el.removeAttribute('aria-current');
      });
    }
    function mountActeStructureBar(mode){
      demSyncFromBarsBeforeActe();
      demHideQuickResults();
      var inner = document.getElementById('search-input-inner');
      var zone = document.getElementById('search-input-zone');
      if (!inner || !zone) return;
      if (inner.getAttribute('data-dem-special') === '1') inner.innerHTML = demActeSearchInnerHTML;
      inner.setAttribute('data-dem-slot', 'acte');
      inner.removeAttribute('data-dem-special');
      zone.setAttribute('data-dem-mode', mode);
      var sq = document.getElementById('search-q');
      if (sq) {
        sq.value = savedSearchQ;
        if (mode === 'acte') {
          sq.placeholder = 'Ex: NFS, Glycémie, IRM, Scanner…';
          sq.setAttribute('aria-label', 'Rechercher un acte médical');
        } else {
          sq.placeholder = 'Nom de la structure ou zone (Mermoz, Plateau, Almadies…)';
          sq.setAttribute('aria-label', 'Rechercher une structure ou une zone');
        }
      }
      initHealthcareSearchAutocomplete();
    }
    function demPriceHidden(){
      return {
        min: document.getElementById('sipn-inp-price-min') || document.getElementById('inp-price-min') || document.getElementById('inp-price-min-mob'),
        max: document.getElementById('sipn-inp-price-max') || document.getElementById('inp-price-max') || document.getElementById('inp-price-max-mob'),
      };
    }
    function mountBudgetBar(){
      var inner = document.getElementById('search-input-inner');
      var zone = document.getElementById('search-input-zone');
      if (!inner || !zone) return;
      demSyncFromBarsBeforeActe();
      var cur = document.getElementById('search-q');
      if (cur) savedSearchQ = cur.value;
      zone.setAttribute('data-dem-mode', 'budget');
      inner.setAttribute('data-dem-special', '1');
      inner.removeAttribute('data-dem-slot');
      var priceH = demPriceHidden();
      var pm = priceH.max;
      var inpMin = priceH.min;
      var elSl = document.getElementById('price-slider') || document.getElementById('price-slider-mob');
      var lo = (inpMin && inpMin.value) ? parseFloat(inpMin.value) : PMIN;
      if (isNaN(lo)) lo = PMIN;
      var hiInit = (pm && pm.value) ? parseFloat(pm.value) : 50000;
      if (isNaN(hiInit)) hiInit = 50000;
      hiInit = Math.min(Math.max(hiInit, PMIN), PMAX);
      var qr = document.getElementById('quick-results');
      inner.innerHTML = '<div class="dem-budget-range-wrap w-full min-w-0">' +
        '<p class="mb-2 text-[11px] leading-relaxed text-gray-600">Glissez le curseur : les actes avec au moins une offre à ce plafond s’affichent sous la zone de recherche (comme sur la démo). Cliquez un acte pour l’ouvrir dans les résultats.</p>' +
        '<div class="mb-1 text-xs font-semibold text-gray-800" id="dem-budget-label">Budget max : ' + demFmtF(hiInit) + ' FCFA</div>' +
        '<input type="range" id="dem-budget-range" class="dem-budget-range-input h-2 w-full cursor-pointer accent-[var(--mc-accent, #4fa3c7)]" ' +
        'min="' + PMIN + '" max="' + PMAX + '" step="1000" value="' + hiInit + '">' +
        '<div class="mt-1 flex justify-between text-[10px] text-gray-500"><span>' + demFmtF(PMIN) + ' F</span><span>' + demFmtF(PMAX) + ' F</span></div>' +
        '<button type="button" id="dem-budget-apply" class="btn-accent mt-3 w-full rounded-xl py-2.5 text-sm font-bold">Appliquer ce plafond (filtre + résultats)</button>' +
        '</div>';
      var rng = document.getElementById('dem-budget-range');
      var lbl = document.getElementById('dem-budget-label');
      function demGoActeBudget(acteId, maxVal){
        var u = new URLSearchParams(window.location.search);
        u.set('acte', String(acteId));
        u.set('price_max', String(Math.round(maxVal)));
        u.delete('page');
        window.location.href = window.location.pathname + '?' + u.toString() + '#results-col';
      }
      function renderBudgetQuick(hi){
        if (!qr) return;
        var url = budgetApiUrl + '?max=' + encodeURIComponent(String(Math.round(hi)));
        var svc = (new URLSearchParams(window.location.search)).get('service');
        if (svc) url += '&service=' + encodeURIComponent(svc);
        try {
          var fd = new FormData(form);
          fd.getAll('assurance').forEach(function(aid){ url += '&assurance=' + encodeURIComponent(aid); });
        } catch (e) {}
        fetch(url, { credentials: 'same-origin' })
          .then(function(r){ return r.json(); })
          .then(function(d){
            var actes = d.actes || [];
            qr.classList.remove('hidden');
            if (!actes.length){
              qr.innerHTML = '<div class="dem-qr-budget dem-qr-budget--empty rounded-xl border border-amber-100 bg-amber-50/80 p-3 text-xs text-amber-900">Aucune offre à ce plafond avec les filtres actuels. Augmentez le budget ou retirez une assurance.</div>';
              return;
            }
            var head = '<div class="text-[11px] font-semibold text-gray-800">' + actes.length + ' acte' + (actes.length > 1 ? 's' : '') + ' à ce budget — cliquez pour afficher les structures</div>';
            var grid = '<div class="dem-qr-grid mt-2 grid max-h-56 gap-2 overflow-y-auto sm:grid-cols-2">' + actes.map(function(f){
              return '<button type="button" class="dem-qr-item w-full rounded-xl border border-gray-200 bg-white px-2.5 py-2 text-left text-xs shadow-sm transition hover:border-accent-400 hover:bg-accent-50/50" data-dem-budget-acte="' + f.id + '">' +
                '<span class="block truncate font-semibold text-gray-900">' + demEscapeAttr(f.name) + '</span>' +
                '<span class="mt-0.5 block text-[10px] text-gray-500">dès ' + Math.round(f.min_price).toLocaleString('fr-FR') + ' F · ' + f.n_struct + ' struct.</span></button>';
            }).join('') + '</div>';
            qr.innerHTML = '<div class="dem-qr-budget rounded-xl border border-gray-200 bg-gray-50/90 p-3 shadow-sm">' + head + grid + '</div>';
            qr.querySelectorAll('[data-dem-budget-acte]').forEach(function(btn){
              btn.addEventListener('click', function(){
                demGoActeBudget(btn.getAttribute('data-dem-budget-acte'), hi);
              });
            });
          })
          .catch(function(){
            if (qr) { qr.classList.remove('hidden'); qr.innerHTML = '<div class="text-xs text-red-600">Impossible de charger les actes.</div>'; }
          });
      }
      var debT = null;
      function scheduleBudgetQuick(hi){
        clearTimeout(debT);
        debT = setTimeout(function(){ renderBudgetQuick(hi); }, 300);
      }
      rng.addEventListener('input', function(){
        var hi = parseFloat(rng.value);
        if (lbl) lbl.textContent = 'Budget max : ' + demFmtF(hi) + ' FCFA';
        scheduleBudgetQuick(hi);
      });
      scheduleBudgetQuick(parseFloat(rng.value));
      document.getElementById('dem-budget-apply').addEventListener('click', function(){
        var hi = parseFloat(rng.value);
        var priceH = demPriceHidden();
        var inpMax = priceH.max;
        var inpMinEl = priceH.min;
        var minStr = lo <= PMIN ? '' : String(Math.round(lo));
        var maxStr = hi >= PMAX ? '' : String(Math.round(hi));
        if (inpMax) inpMax.value = maxStr;
        if (inpMinEl) inpMinEl.value = minStr;
        if (elSl && elSl.noUiSlider) elSl.noUiSlider.set([lo, Math.min(hi, PMAX)]);
        form.submit();
      });
    }
    function mountAssuranceBar(){
      var inner = document.getElementById('search-input-inner');
      var zone = document.getElementById('search-input-zone');
      var center = demAssuranceCenter();
      if (!inner || !zone || !center) return;
      demSyncFromBarsBeforeActe();
      demHideQuickResults();
      var cur = document.getElementById('search-q');
      if (cur) savedSearchQ = cur.value;
      var valsPre = window.jQuery && jQuery(center).val ? jQuery(center).val() : Array.from(center.selectedOptions).map(function(o){ return o.value; });
      if (valsPre && !Array.isArray(valsPre)) valsPre = [valsPre];
      center.disabled = true;
      zone.setAttribute('data-dem-mode', 'assurance');
      inner.setAttribute('data-dem-special', '1');
      inner.removeAttribute('data-dem-slot');
      inner.innerHTML = '<div class="w-full min-w-0">' +
        '<label for="dem-bar-assurance" class="mb-1 block text-[10px] font-bold uppercase tracking-wide text-gray-500">Mutuelle ou assurance</label>' +
        '<select multiple id="dem-bar-assurance" class="dem-field s2-multi-dem-bar w-full text-sm" aria-label="Mutuelles et assurances"></select>' +
        '</div>';
      var bar = document.getElementById('dem-bar-assurance');
      bar.innerHTML = center.innerHTML;
      if (valsPre && valsPre.length) {
        Array.from(bar.options).forEach(function(o){ o.selected = valsPre.indexOf(o.value) !== -1; });
      }
      if (window.jQuery) {
        var $bar = jQuery(bar);
        $bar.select2({ placeholder: 'Rechercher une mutuelle…', allowClear: true, width: '100%', closeOnSelect: false });
        var s2AssT = null;
        $bar.on('select2:select select2:unselect select2:clear', function(){
          if (window.__suppressAutoFilterSubmit) return;
          clearTimeout(s2AssT);
          s2AssT = setTimeout(function(){ form.submit(); }, 400);
        });
      }
    }
    function mountDelaiBar(){
      var inner = document.getElementById('search-input-inner');
      var zone = document.getElementById('search-input-zone');
      var master = demDelaiMaster();
      if (!inner || !zone || !master) return;
      demSyncFromBarsBeforeActe();
      demHideQuickResults();
      var cur = document.getElementById('search-q');
      if (cur) savedSearchQ = cur.value;
      master.disabled = true;
      zone.setAttribute('data-dem-mode', 'delai');
      inner.setAttribute('data-dem-special', '1');
      inner.removeAttribute('data-dem-slot');
      inner.innerHTML = '<div class="w-full min-w-0">' +
        '<label class="mb-1 block text-[10px] font-bold uppercase tracking-wide text-gray-500">Délai maximal</label>' +
        '<select name="delai" id="dem-bar-delai" class="dem-field w-full py-2.5 text-sm" aria-label="Délai maximal"></select>' +
        '<button type="submit" class="btn-accent mt-3 w-full rounded-xl py-2.5 text-sm font-bold">Rechercher</button>' +
        '</div>';
      var bar = document.getElementById('dem-bar-delai');
      bar.innerHTML = master.innerHTML;
      bar.value = master.value;
    }
    function mountZoneBar(){
      var inner = document.getElementById('search-input-inner');
      var zone = document.getElementById('search-input-zone');
      if (!inner || !zone) return;
      demSyncFromBarsBeforeActe();
      demHideQuickResults();
      var cur = document.getElementById('search-q');
      if (cur) savedSearchQ = cur.value;
      var cDesk = document.getElementById('city-input-desk');
      var cQuick = document.getElementById('city-quick');
      var curCity = (cDesk && cDesk.value) || (cQuick && cQuick.value) || '';
      if (cDesk) cDesk.disabled = true;
      if (cQuick) cQuick.disabled = true;
      zone.setAttribute('data-dem-mode', 'zone');
      inner.setAttribute('data-dem-special', '1');
      inner.removeAttribute('data-dem-slot');
      inner.innerHTML = '<div class="w-full min-w-0 space-y-3">' +
        '<label class="block text-[10px] font-bold uppercase tracking-wide text-gray-500">Ville ou quartier</label>' +
        '<input type="text" name="city" id="dem-bar-city" list="city-options" autocomplete="address-level2" ' +
        'class="dem-field w-full py-2.5 text-sm" placeholder="Dakar, Mermoz, Thiès…" value="' + demEscapeAttr(curCity) + '">' +
        '<button type="button" id="dem-zone-geo" class="btn-accent w-full rounded-xl py-2.5 text-sm font-bold"><i class="ti ti-antenna"></i> Utiliser ma position</button>' +
        '<button type="submit" class="w-full rounded-xl border border-gray-200 bg-white py-2.5 text-sm font-semibold text-gray-800">Rechercher</button>' +
        '</div>';
      document.getElementById('dem-zone-geo').addEventListener('click', function(){
        if (!navigator.geolocation) {
          if (location.protocol === 'http:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            alert("La géolocalisation nécessite une connexion sécurisée (HTTPS). Utilisez la recherche d'adresse.");
          } else {
            alert('Géolocalisation indisponible sur ce navigateur.');
          }
          return;
        }
        var btn = document.getElementById('dem-zone-geo');
        var prev = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Localisation…';
        navigator.geolocation.getCurrentPosition(function(p){
          if (window.setCoords) {
            window.setCoords(p.coords.latitude.toFixed(6), p.coords.longitude.toFixed(6), true);
          }
          btn.disabled = false;
          btn.textContent = prev;
        }, function(err){
          btn.disabled = false;
          btn.textContent = prev;
          if (location.protocol === 'http:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
            alert("La géolocalisation nécessite une connexion sécurisée (HTTPS). Utilisez la recherche d'adresse.");
            return;
          }
          var msg = 'Position refusée ou indisponible.';
          if (err) {
            if (err.code === 1) msg = 'Autorisation GPS refusée. Activez la localisation dans votre navigateur.';
            else if (err.code === 2) msg = 'Position GPS momentanément indisponible.';
            else if (err.code === 3) msg = 'Délai GPS dépassé. Veuillez réessayer.';
          }
          alert(msg);
        }, { enableHighAccuracy: true, timeout: 15000 });
      });
    }
    function applyDemSearchMode(mode){
      setModeActive(mode);
      if (mode === 'acte' || mode === 'structure') { mountActeStructureBar(mode); return; }
      if (mode === 'budget') { mountBudgetBar(); return; }
      if (mode === 'assurance') { mountAssuranceBar(); return; }
      if (mode === 'delai') { mountDelaiBar(); return; }
      if (mode === 'zone') { mountZoneBar(); return; }
    }
    var inner0 = document.getElementById('search-input-inner');
    if (inner0) {
      demActeSearchInnerHTML = inner0.innerHTML;
      var sq0 = document.getElementById('search-q');
      if (sq0) {
        sq0.placeholder = 'Ex: NFS, Glycémie, IRM, Scanner…';
        sq0.setAttribute('aria-label', 'Rechercher un acte médical');
      }
    }
    form.querySelectorAll('[data-dem-search-mode]').forEach(function(el){
      var mode = el.getAttribute('data-dem-search-mode');
      if (!mode) return;
      el.addEventListener('click', function(e){
        e.preventDefault();
        applyDemSearchMode(mode);
      });
    });

    /* Dropdown filtres desktop */
    (function initDemDesktopFilterDropdown(){
      var activeDrop = null;
      var budgetTimer = null;

      function getDd() { return document.getElementById('sipn-filter-dropdown'); }
      function getForm() { return document.getElementById('search-form'); }

      function syncAssuranceToHidden(){
        var dd = getDd();
        var form = getForm();
        if (!dd || !form) return;
        var center = demAssuranceCenter();
        var checked = Array.from(dd.querySelectorAll('.sipn-assurance-cb:checked')).map(function(c){ return c.value; });
        if (center) {
          if (window.jQuery) jQuery(center).val(checked).trigger('change');
          else Array.from(center.options).forEach(function(o){ o.selected = checked.indexOf(o.value) !== -1; });
        }
        form.querySelectorAll('input[name="assurance"].dem-sync-hidden').forEach(function(n){ n.remove(); });
        checked.forEach(function(v){
          var h = document.createElement('input');
          h.type = 'hidden'; h.name = 'assurance'; h.value = v; h.className = 'dem-sync-hidden';
          form.appendChild(h);
        });
      }

      function closeDrop(){
        activeDrop = null;
        var dd = getDd();
        if (!dd) return;
        dd.classList.add('hidden');
        dd.hidden = true;
        dd.querySelectorAll('[data-sipn-panel]').forEach(function(p){ p.hidden = true; });
      }

      function showPanel(type){
        var dd = getDd();
        if (!dd) return false;
        dd.querySelectorAll('[data-sipn-panel]').forEach(function(p){ p.hidden = true; });
        var panel = dd.querySelector('[data-sipn-panel="' + type + '"]');
        if (!panel) return false;
        panel.hidden = false;
        dd.classList.remove('hidden');
        dd.hidden = false;
        return true;
      }

      window.toggleDemFilterDropdown = function(type){
        if (activeDrop === type) { closeDrop(); return; }
        if (!showPanel(type)) return;
        activeDrop = type;
        var chip = document.querySelector('[data-dem-filter-drop="' + type + '"]');
        var dd = getDd();
        if (chip && dd && dd.parentElement) {
          var chipRect = chip.getBoundingClientRect();
          var parentRect = dd.parentElement.getBoundingClientRect();
          var leftOffset = Math.max(0, chipRect.left - parentRect.left);
          if (leftOffset + 350 > parentRect.width) {
            leftOffset = Math.max(0, parentRect.width - 360);
          }
          dd.style.left = leftOffset + 'px';
        }
      };
      window.closeDemFilterDropdown = closeDrop;

      function submitDemFilterForm(){
        var form = getForm();
        if (!form) return;
        var urlParams = new URLSearchParams(window.location.search);
        var urlActes = urlParams.getAll('acte');
        if (urlActes.length) {
          var existingActes = Array.from(form.querySelectorAll('input[name="acte"]')).map(function(i){ return i.value; });
          urlActes.forEach(function(aid){
            if (existingActes.indexOf(aid) === -1) {
              var h = document.createElement('input');
              h.type = 'hidden';
              h.name = 'acte';
              h.value = aid;
              form.appendChild(h);
            }
          });
        }
        form.submit();
      }

      function applyBudget(hi){
        var form = getForm();
        var priceH = demPriceHidden();
        var inpMax = priceH.max;
        var inpMin = priceH.min;
        var maxStr = hi >= PMAX ? '' : String(Math.round(hi));
        if (inpMax) inpMax.value = maxStr;
        if (inpMin) inpMin.value = '';
        var budLbl = document.getElementById('dem-dd-budget-lbl');
        if (budLbl) budLbl.textContent = maxStr ? demFmtF(hi) + ' FCFA' : 'Illimité';
        closeDrop();
        if (form) form.submit();
      }

      function executeReset(e){
        if (e) e.preventDefault();
        try {
          sessionStorage.removeItem('sipn_selected_actes');
          sessionStorage.removeItem('sipn_acte_names');
        } catch (err) {}
        window.location.assign(searchUrl);
      }
      window._sipnExecuteReset = executeReset;

      /* Écouteurs globaux délégués sur document */
      document.addEventListener('click', function(e){
        var t = e.target;
        if (!t || !t.closest) return;

        var chip = t.closest('[data-dem-filter-drop]');
        if (chip) {
          e.preventDefault();
          e.stopPropagation();
          var type = chip.getAttribute('data-dem-filter-drop');
          if (type && window.toggleDemFilterDropdown) window.toggleDemFilterDropdown(type);
          return;
        }

        var zonePill = t.closest('[data-dem-zone-pill]');
        if (zonePill) {
          e.preventDefault();
          var val = zonePill.getAttribute('data-dem-zone-pill') || '';
          var cityInp = document.getElementById('sipn-filter-city');
          var currentVal = cityInp ? cityInp.value : '';
          var newVal = (currentVal === val) ? '' : val;
          document.querySelectorAll('input[name="city"]').forEach(function(i){ i.value = newVal; });
          closeDrop();
          submitDemFilterForm();
          return;
        }

        var zoneClear = t.closest('[data-sipn-clear="zone"]');
        if (zoneClear) {
          e.preventDefault();
          document.querySelectorAll('input[name="city"]').forEach(function(i){ i.value = ''; });
          closeDrop();
          submitDemFilterForm();
          return;
        }

        var delaiPill = t.closest('[data-dem-delai-pill]');
        if (delaiPill) {
          e.preventDefault();
          var delVal = delaiPill.getAttribute('data-dem-delai-pill') || '';
          var delSel = document.getElementById('sipn-filter-delai');
          var curDelVal = delSel ? delSel.value : '';
          var newDelVal = (curDelVal === delVal) ? '' : delVal;
          document.querySelectorAll('select[name="delai"]').forEach(function(s){ s.value = newDelVal; });
          closeDrop();
          submitDemFilterForm();
          return;
        }

        var delaiClear = t.closest('[data-sipn-clear="delai"]');
        if (delaiClear) {
          e.preventDefault();
          document.querySelectorAll('select[name="delai"]').forEach(function(s){ s.value = ''; });
          closeDrop();
          submitDemFilterForm();
          return;
        }

        var assPill = t.closest('#sipn-filter-dropdown [data-sipn-panel="assurance"] .dem-filter-pill');
        if (assPill) {
          e.preventDefault();
          e.stopPropagation();
          var cb = assPill.querySelector('.sipn-assurance-cb');
          if (cb) {
            cb.checked = !cb.checked;
            assPill.classList.toggle('on', cb.checked);
          }
          return;
        }

        var assClear = t.closest('[data-sipn-clear="assurance"]');
        if (assClear) {
          e.preventDefault();
          var dd = getDd();
          var assPanel = dd ? dd.querySelector('[data-sipn-panel="assurance"]') : null;
          if (assPanel) {
            assPanel.querySelectorAll('.sipn-assurance-cb').forEach(function(c){ c.checked = false; });
            assPanel.querySelectorAll('.dem-filter-pill').forEach(function(p){ p.classList.remove('on'); });
          }
          syncAssuranceToHidden();
          var form = getForm();
          if (form) form.submit();
          return;
        }

        var assApply = t.closest('[data-sipn-apply="assurance"]');
        if (assApply) {
          e.preventDefault();
          syncAssuranceToHidden();
          closeDrop();
          submitDemFilterForm();
          return;
        }

        var budClear = t.closest('[data-sipn-clear="budget"]');
        if (budClear) {
          e.preventDefault();
          var priceH = demPriceHidden();
          if (priceH.max) priceH.max.value = '';
          if (priceH.min) priceH.min.value = '';
          var budRng = document.getElementById('dem-dd-budget-range');
          var budLbl = document.getElementById('dem-dd-budget-lbl');
          if (budRng) budRng.value = PMAX;
          if (budLbl) budLbl.textContent = 'Illimité';
          closeDrop();
          var form = getForm();
          if (form) form.submit();
          return;
        }

        var resetBtn = t.closest('#fc-reset, .btn-reset-filters, .dem-filter-reset');
        if (resetBtn) {
          executeReset(e);
          return;
        }

        if (activeDrop) {
          if (!t.closest('[data-dem-filter-drop]') && !t.closest('#sipn-filter-dropdown')) {
            closeDrop();
          }
        }
      });

      document.addEventListener('keydown', function(e){
        if (e.key === 'Enter' || e.key === ' ') {
          var chip = e.target && e.target.closest && e.target.closest('[data-dem-filter-drop]');
          if (chip) { e.preventDefault(); chip.click(); }
        }
      });

      document.addEventListener('input', function(e){
        if (e.target && e.target.id === 'dem-dd-budget-range') {
          var budRng = e.target;
          var budLbl = document.getElementById('dem-dd-budget-lbl');
          var hi = parseFloat(budRng.value);
          if (budLbl) budLbl.textContent = hi >= PMAX ? 'Illimité' : demFmtF(hi) + ' FCFA';
          clearTimeout(budgetTimer);
          budgetTimer = setTimeout(function(){ applyBudget(hi); }, 450);
        }
      });

      document.addEventListener('change', function(e){
        if (e.target && e.target.id === 'id-sort-dem') {
          var form = getForm();
          if (form) form.submit();
        }
      });
    })();
  })();

  /* ─── Bouton "Profil →" : redirige vers la fiche structure avec actes en paramètre ─── */
  document.addEventListener('click', function(ev){
    var t = ev.target;
    if (!t || !t.closest) return;
    var link = t.closest('.dem-profil-link');
    if (!link) return;
    ev.preventDefault();
    ev.stopPropagation();
    var baseUrl = link.getAttribute('data-org-url') || link.getAttribute('href') || '#';
    if (!baseUrl || baseUrl === '#') return;
    var u = new URL(baseUrl, window.location.origin);
    var ids = window._sipnGetSelectedIds ? window._sipnGetSelectedIds() : [];
    if (!ids.length) {
      ids = new URLSearchParams(window.location.search).getAll('acte');
    }
    ids.forEach(function(id){ u.searchParams.append('acte', String(id)); });
    window.location.href = u.toString();
  });

  /* ─── Mobile search submit hook ─── */
  (function hcMobileActeSearchSubmit(){
    var form = document.getElementById('search-form');
    if (!form || !document.body.classList.contains('sipn-prestations')) return;
    form.addEventListener('submit', function(e){
      if (!hcIsMobilePrestations()) return;
      var zone = document.getElementById('search-input-zone');
      if (zone && zone.getAttribute('data-dem-mode') !== 'acte') return;
      if (form.querySelector('input[name="acte"]')) return;
      var input = document.getElementById('search-q');
      var q = input ? input.value.trim() : '';
      if (q.length < 2) return;
      e.preventDefault();
      fetch(autocompleteUrl + '?q=' + encodeURIComponent(q), { credentials: 'same-origin' })
        .then(function(r){ return r.json(); })
        .then(function(d){
          var actes = (d.suggestions || []).filter(function(s){ return s.type === 'acte'; });
          var exact = actes.find(function(s){ return s.label.toLowerCase() === q.toLowerCase(); });
          if (exact && exact.id) { hcGoActeResults(exact.id); return; }
          if (actes.length === 1 && actes[0].id) { hcGoActeResults(actes[0].id); return; }
          var u = new URL(searchUrl, window.location.origin);
          var fd = new FormData(form);
          fd.delete('page');
          fd.forEach(function(v, k){ if (v !== '' && v != null) u.searchParams.append(k, v); });
          u.hash = 'results-col';
          window.location.href = u.toString();
        })
        .catch(function(){
          var u = new URL(searchUrl, window.location.origin);
          var fd = new FormData(form);
          fd.delete('page');
          fd.forEach(function(v, k){ if (v !== '' && v != null) u.searchParams.append(k, v); });
          u.hash = 'results-col';
          window.location.href = u.toString();
        });
    });
  })();

  /* Initialiser l'autocomplétion */
  initHealthcareSearchAutocomplete();

  /* ─── Lots prédéfinis ──────────────────────────────────────────── */
  (function initPresets(){
    var presetsList = cfg.presets || [];
    var selectedLotIds = cfg.selectedLotIds || [];
    var el = document.getElementById('preset-scroll-search');
    var btnPrev = document.getElementById('preset-scroll-prev');
    var btnNext = document.getElementById('preset-scroll-next');
    function escapeHtml(s){ var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

    function presetScrollStep(){
      if (!el) return 240;
      return Math.max(200, Math.min(360, Math.floor(el.clientWidth * 0.72)));
    }
    function presetArrowsUi(){
      if (!el || !btnPrev || !btnNext) return;
      var overflow = el.scrollWidth > el.clientWidth + 6;
      btnPrev.classList.toggle('is-hidden-overflow', !overflow);
      btnNext.classList.toggle('is-hidden-overflow', !overflow);
      if (!overflow){
        btnPrev.disabled = true;
        btnNext.disabled = true;
        return;
      }
      var max = el.scrollWidth - el.clientWidth;
      var x = el.scrollLeft;
      btnPrev.disabled = x <= 2;
      btnNext.disabled = x >= max - 2;
    }

    if (!el || !presetsList || !presetsList.length) return;

    if (btnPrev){
      btnPrev.addEventListener('click', function(){
        el.scrollBy({left: -presetScrollStep(), behavior: 'smooth'});
      });
    }
    if (btnNext){
      btnNext.addEventListener('click', function(){
        el.scrollBy({left: presetScrollStep(), behavior: 'smooth'});
      });
    }
    el.addEventListener('scroll', function(){ requestAnimationFrame(presetArrowsUi); });
    window.addEventListener('resize', function(){ presetArrowsUi(); });

    presetsList.forEach(function(p){
      var isSelected = selectedLotIds.indexOf(p.id) !== -1;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'shrink-0 cursor-pointer rounded-xl border px-4 py-3 text-left shadow-sm transition w-44 sm:w-52 ' +
        (isSelected ? 'border-accent-500 bg-accent-50 ring-2 ring-accent-300/80' : 'border-gray-200 bg-white hover:border-accent-300 hover:shadow-md');
      btn.innerHTML = '<span class="text-xl">' + (p.icon || '<i class="ti ti-clipboard-list"></i>') + '</span>' +
        '<div class="mt-1 truncate font-semibold text-gray-900 text-sm">' + escapeHtml(p.name) + '</div>' +
        '<div class="line-clamp-2 text-xs text-gray-500">' + escapeHtml(p.teaser || '') + '</div>';
      btn.addEventListener('click', function(){
        var ids = p.acte_ids || [];
        fetch(bundleSaveUrl, {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken()},
          body: JSON.stringify({acte_ids: ids})
        })
          .catch(function(){}).finally(function(){
            var params = new URLSearchParams();
            params.set('sort', 'price_asc');
            ids.forEach(function(id){ params.append('acte', id); });
            params.append('lot', String(p.id));
            window.location.href = searchUrl + '?' + params.toString();
          });
      });
      el.appendChild(btn);
    });
    presetArrowsUi();
  })();

  /* ─── Effacer la requête ──────────────────────────────────────── */
  var clearQ = $('#btn-clear-q');
  if (clearQ) clearQ.addEventListener('click', function(){
    var inp = $('#search-q');
    if (inp){ inp.value = ''; var sf = document.getElementById('search-form'); if (sf) sf.submit(); }
  });

  /* ─── Effacer la ville rapide ─────────────────────────────────── */
  var clearCity = $('#btn-clear-city');
  if (clearCity) clearCity.addEventListener('click', function(){
    $$('input[name="city"]').forEach(function(i){ i.value = ''; });
    var sf = document.getElementById('search-form');
    if (sf) sf.submit();
  });

  /* ─── Synchroniser tous les inputs name="city" entre eux ──────── */
  (function(){
    var inputs = $$('input[name="city"]');
    if (!inputs.length) return;
    inputs.forEach(function(src){
      src.addEventListener('change', function(){
        inputs.forEach(function(dst){ if (dst !== src) dst.value = src.value; });
        var sf = document.getElementById('search-form');
        if (sf) sf.submit();
      });
    });
    var form = $('#search-form');
    if (form) form.addEventListener('submit', function(){
      var v = '';
      inputs.forEach(function(i){ if (!v && i.value) v = i.value; });
      inputs.forEach(function(i){ i.value = v; });
    });
  })();

  /* ─── Chips filtres actifs (basé sur l'URL courante) ──────────── */
  (function initActiveFilterChips(){
    var box = $('#active-chips'); if (!box) return;
    var p = new URLSearchParams(window.location.search);
    function urlWithout(keys){
      var p2 = new URLSearchParams(window.location.search);
      keys.forEach(function(k){ p2.delete(k); });
      p2.delete('page');
      return '?' + p2.toString();
    }
    function chip(label, removeUrl){
      var s = document.createElement('span');
      s.className = 'filter-chip';
      s.innerHTML = '<span class="truncate max-w-[180px]">' + label + '</span>' +
        '<a href="' + removeUrl + '" title="Retirer">×</a>';
      box.appendChild(s);
    }
    if (p.get('q')) chip('Recherche : ' + p.get('q'), urlWithout(['q']));
    if (p.get('city')) chip('Ville : ' + p.get('city'), urlWithout(['city']));
    if (p.get('proximity') === '1' && p.get('lat')) chip('À proximité', urlWithout(['proximity','lat','lng','radius_km']));
    if (p.get('price_min') || p.get('price_max')) chip('Prix ' + (p.get('price_min')||'min') + ' – ' + (p.get('price_max')||'max'), urlWithout(['price_min','price_max']));
    var assr = p.getAll('assurance'); if (assr.length) chip(assr.length + ' assurance' + (assr.length>1?'s':''), urlWithout(['assurance']));
    var rgs = p.getAll('region'); if (rgs.length) chip(rgs.length + ' région' + (rgs.length>1?'s':''), urlWithout(['region']));
    var tps = p.getAll('type'); if (tps.length) chip(tps.length + ' type' + (tps.length>1?'s':''), urlWithout(['type']));
    var delaiLabels = {immediat:'Immédiat',"30min":"≤ 30 min","1h":"≤ 1 h","2h":"≤ 2 h","4h":"≤ 4 h","24h":"≤ 24 h","48h":"≤ 48 h","72h":"≤ 72 h","7j":"≤ 7 j",rdv:"Sur RDV"};
    if (p.get('delai')) chip('Délai : ' + (delaiLabels[p.get('delai')] || p.get('delai')), urlWithout(['delai']));
    if (p.get('domicile') === '1') chip('Prestations à domicile', urlWithout(['domicile']));
    if (box.children.length) {
      var reset = document.createElement('a');
      reset.href = searchUrl; reset.className = 'text-xs font-semibold text-gray-500 underline';
      reset.textContent = 'Tout effacer';
      box.appendChild(reset);
    } else {
      box.style.display = 'none';
    }
  })();

  /* ─── Sélection pilier instantanée sans rechargement ───────────── */
  (function initInstantPillars() {
    function isAmbulancePillar(btn) {
      return btn.getAttribute('data-is-ambulance') === '1';
    }
    function applyPillarUi(targetSid, ambActive) {
      document.querySelectorAll('.dem-pbtn').forEach(function(b) {
        var bSid = b.getAttribute('data-service-id');
        b.classList.toggle('active', (targetSid ? bSid === targetSid : !bSid));
      });
      document.querySelectorAll('.dem-acte-family').forEach(function(fam) {
        var famSid = fam.getAttribute('data-service-id');
        if (!targetSid || famSid === targetSid) {
          fam.style.display = '';
          if (targetSid) fam.open = true;
        } else {
          fam.style.display = 'none';
        }
      });
      var ambBanner = document.getElementById('dem-ambulance-banner');
      if (ambBanner) ambBanner.style.display = ambActive ? 'block' : 'none';
    }
    document.querySelectorAll('.dem-pbtn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        var targetSid = btn.getAttribute('data-service-id');
        e.preventDefault();
        applyPillarUi(targetSid, isAmbulancePillar(btn));
        var u = new URL(window.location.href);
        if (targetSid) u.searchParams.set('service', targetSid);
        else u.searchParams.delete('service');
        u.hash = targetSid ? 'sidebar-desktop' : '';
        var hasActes = u.searchParams.getAll('acte').length > 0;
        if (hasActes && history.replaceState) {
          history.replaceState(null, '', u.toString());
        } else {
          window.location.assign(u.toString());
        }
      });
    });
    (function syncPillarFromUrl(){
      var u = new URL(window.location.href);
      var sid = u.searchParams.get('service') || '';
      var activeBtn = null;
      document.querySelectorAll('.dem-pbtn').forEach(function(b){
        var bSid = b.getAttribute('data-service-id') || '';
        if (sid ? bSid === sid : !bSid) activeBtn = b;
      });
      if (activeBtn) applyPillarUi(activeBtn.getAttribute('data-service-id') || '', isAmbulancePillar(activeBtn));
      if (sid) {
        var targetFam = document.querySelector('.dem-acte-family[data-service-id="' + sid + '"]');
        if (targetFam) {
          targetFam.open = true;
          setTimeout(function() {
            targetFam.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          }, 150);
        }
      }
    })();
  })();

  /* ─── Transmission des actes sélectionnés aux cartes Profil Établissement ─── */
  (function initOrgProfileLinksSync() {
    function syncLinks() {
      var u = new URL(window.location.href);
      var actParams = u.searchParams.getAll('acte');
      if (!actParams.length) return;
      
      document.querySelectorAll('a[href*="/structure/"], a[href*="/organismes/"], a.dem-org-profile-link, a.dem-profil-link').forEach(function(link) {
        if (link.classList.contains('dem-profil-link')) {
          var base = link.getAttribute('data-org-url');
          if (!base) return;
          try {
            var profUrl = new URL(base, window.location.origin);
            profUrl.searchParams.delete('acte');
            actParams.forEach(function(id) { profUrl.searchParams.append('acte', id); });
            link.setAttribute('data-org-url', profUrl.pathname + profUrl.search);
            link.setAttribute('href', profUrl.pathname + profUrl.search);
          } catch (err) {}
          return;
        }
        try {
          var targetUrl = new URL(link.href, window.location.origin);
          targetUrl.searchParams.delete('acte');
          actParams.forEach(function(id) {
            targetUrl.searchParams.append('acte', id);
          });
          link.href = targetUrl.toString();
        } catch (err) {}
      });
    }
    syncLinks();
    window.addEventListener('popstate', syncLinks);
  })();

})();

