/**
 * MedCare - Search Mobile UI & Navigation
 * Gère l'expérience mobile & responsive de la recherche :
 * - Bottom sheets (filtres, panier démo)
 * - Navigation par onglets (Prestations, Résultats, Panier, Messages, Menu)
 * - Grille des piliers & sélection mobile d'actes
 * - Prévisualisation express d'organisme
 * - Modale position, géolocalisation GPS & géocodage
 */
(function(){
  'use strict';

  var cfg = window.SIPN_CONFIG || {};
  var urls = cfg.urls || {};

  var messagingInboxUrl = urls.messagingInbox || '/messages/';
  var previewUrlTpl = urls.organismePreviewTpl || '/api/organisme/org-preview-slug-tmp/preview/';
  var apiReverseUrl = urls.apiReverse || '/api/reverse/';
  var apiGeocodeUrl = urls.apiGeocode || '/api/geocode/';
  var saveSearchLocationUrl = urls.saveSearchLocation || '/save-search-location/';

  function getCookie(name){
    return window.SIPNUtils ? window.SIPNUtils.getCookie(name) : '';
  }
  function getCsrfToken(){
    return window.SIPNUtils ? window.SIPNUtils.getCsrfToken() : '';
  }
  function $(s, p){ return (p || document).querySelector(s); }
  function $$(s, p){ return Array.prototype.slice.call((p || document).querySelectorAll(s)); }

  /* ─── Bottom-sheet filtres mobile ──────────────────────────────── */
  (function(){
    var fab = $('#fab-filters'), sheet = $('#sheet-panel'), bd = $('#sheet-backdrop'), btnClose = $('#sheet-close');
    function open(){
      if (window._closeCartSheet) window._closeCartSheet();
      if (sheet) sheet.classList.add('open');
      if (bd) bd.classList.add('open');
      document.body.classList.add('sheet-locked');
    }
    function close(){
      if (sheet) sheet.classList.remove('open');
      if (bd) bd.classList.remove('open');
      document.body.classList.remove('sheet-locked');
    }
    if (fab) fab.addEventListener('click', open);
    if (btnClose) btnClose.addEventListener('click', close);
    if (bd) bd.addEventListener('click', close);
    window._closeFilterSheet = close;
  })();

  /* ─── Bottom-sheet panier (mode démo mobile) ─────────────────── */
  (function(){
    var btnOpenF = document.getElementById('dem-mq-open-filters');
    var btnCart = document.getElementById('dem-mq-open-cart');
    var sheet = document.getElementById('dem-cart-sheet');
    var bd = document.getElementById('dem-cart-backdrop');
    var btnClose = document.getElementById('dem-cart-sheet-close');
    if (!btnOpenF && !btnCart) return;
    function openFilters(e){
      if (e) e.preventDefault();
      if (window._closeCartSheet) window._closeCartSheet();
      var fab = document.getElementById('fab-filters');
      if (fab) fab.click();
    }
    function openCart(e){
      if (e) e.preventDefault();
      if (window._closeFilterSheet) window._closeFilterSheet();
      if (sheet) sheet.classList.add('open');
      if (bd) bd.classList.add('open');
      document.body.classList.add('sheet-locked');
      if (btnCart) btnCart.setAttribute('aria-expanded', 'true');
    }
    function closeCart(){
      if (sheet) sheet.classList.remove('open');
      if (bd) bd.classList.remove('open');
      document.body.classList.remove('sheet-locked');
      if (btnCart) btnCart.setAttribute('aria-expanded', 'false');
    }
    if (btnOpenF) btnOpenF.addEventListener('click', openFilters);
    if (btnCart && document.body.classList.contains('sipn-prestations')) {
      btnCart.addEventListener('click', function(e){
        e.preventDefault();
        if (window._sipnGoPanierTab) window._sipnGoPanierTab();
      });
    } else if (btnCart && sheet) {
      btnCart.addEventListener('click', openCart);
    }
    if (btnClose) btnClose.addEventListener('click', closeCart);
    if (bd) bd.addEventListener('click', closeCart);
    window._closeCartSheet = closeCart;
    window._sipnOpenCartSheet = openCart;
  })();

  /* ─── Vue Prestations / Résultats (mobile + tablette) ───────────── */
  (function(){
    var mqView = window.matchMedia('(max-width: 1023px)');
    var searchForm = document.getElementById('search-form');
    if (!searchForm || !document.body.classList.contains('sipn-prestations')) return;

    function showPrestationsView(push){
      if (!mqView.matches) {
        document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-results', 'sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
        return;
      }
      document.body.classList.add('sipn-mobile-view-prestations');
      document.body.classList.remove('sipn-mobile-view-results', 'sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
      if (push && history.replaceState) {
        var u = window.location.pathname + window.location.search;
        history.replaceState(null, '', u);
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
      if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
    }

    function showResultsView(push){
      if (!mqView.matches) return;
      document.body.classList.add('sipn-mobile-view-results');
      document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
      if (push && history.replaceState) {
        history.replaceState(null, '', window.location.pathname + window.location.search + '#results-col');
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
      if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
      if (window._sipnCheckMissingCart) window._sipnCheckMissingCart();
    }

    function urlImpliesResults(){
      return window.hcSearchUrlImpliesResults ? window.hcSearchUrlImpliesResults() : false;
    }

    function applyMobileView(){
      if (!mqView.matches) {
        document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-results', 'sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
        return;
      }
      var hasActes = document.body.classList.contains('sipn-has-actes');
      if (hasActes && urlImpliesResults()) showResultsView(false);
      else showPrestationsView(false);
    }

    document.addEventListener('click', function(ev){
      if (!mqView.matches || !ev.target || !ev.target.closest) return;
      if (ev.target.closest('.ctx-bar')) {
        var rect = ev.target.closest('.ctx-bar').getBoundingClientRect();
        if (ev.clientY - rect.top < 42) showPrestationsView(true);
      }
    });

    window.addEventListener('hashchange', applyMobileView);
    if (mqView.addEventListener) mqView.addEventListener('change', applyMobileView);
    applyMobileView();

    window._sipnShowPrestations = showPrestationsView;
    window._sipnShowResults = showResultsView;
  })();

  /* ─── Mobile : grille piliers + actes à cocher ───────────────────── */
  (function(){
    var mq = window.matchMedia('(max-width: 1023px)');
    var gridEl = document.getElementById('sipn-pgrid');
    if (!gridEl) return;

    function mountMobileFabs(){
      var fabRoot = document.querySelector('.sipn-mobile-fabs');
      var tabBar = document.getElementById('medcare-tab-bar');
      if (!fabRoot || fabRoot.dataset.sipnMounted === '1') return;
      var parent = tabBar && tabBar.parentNode ? tabBar.parentNode : document.body;
      if (tabBar) parent.insertBefore(fabRoot, tabBar);
      else document.body.appendChild(fabRoot);
      fabRoot.dataset.sipnMounted = '1';
    }
    mountMobileFabs();

    var piliers = [];
    var selected = new Set();
    var curPilier = null;
    var acteNames = {};

    try {
      piliers = JSON.parse(document.getElementById('sipn-mobile-piliers-data').textContent || '[]');
    } catch (e) { piliers = []; }
    try {
      JSON.parse(document.getElementById('sipn-mobile-selected-data').textContent || '[]').forEach(function(id){
        selected.add(String(id));
      });
    } catch (e2) {}

    piliers.forEach(function(p){
      (p.cats || []).forEach(function(cat){
        (cat.actes || []).forEach(function(a){
          acteNames[String(a.pk)] = a.name;
        });
      });
    });

    function escapeHtml(s){
      if (s == null) return '';
      var d = document.createElement('div');
      d.textContent = String(s);
      return d.innerHTML;
    }

    function countSelectedInPilier(pk){
      var pilier = piliers.find(function(p){ return p.id === pk; });
      if (!pilier) return 0;
      var n = 0;
      (pilier.cats || []).forEach(function(cat){
        (cat.actes || []).forEach(function(a){
          if (selected.has(String(a.pk))) n++;
        });
      });
      return n;
    }

    function updatePilierBadge(pk){
      var btn = document.getElementById('pbtn-' + pk);
      if (!btn) return;
      var cnt = countSelectedInPilier(pk);
      var badge = btn.querySelector('.pgrid-badge');
      if (badge) {
        badge.textContent = cnt;
        badge.classList.toggle('show', cnt > 0);
      }
      btn.classList.toggle('active', curPilier === pk || cnt > 0);
    }

    function syncResultsHeader(){
      var rhActe = document.getElementById('rh-acte-m');
      var rhSub = document.getElementById('rh-sub-m');
      if (!rhActe || !rhSub) return;
      if (!selected.size) {
        rhActe.textContent = 'Sélectionnez un acte';
        rhSub.textContent = 'Cherchez un acte depuis Prestations';
        return;
      }
      if (selected.size === 1) {
        var pk = Array.from(selected)[0];
        rhActe.textContent = acteNames[pk] || ('Acte #' + pk);
        rhSub.textContent = 'Structure(s) disponible(s) pour cet examen';
      } else {
        rhActe.textContent = selected.size + ' examens sélectionnés';
        rhSub.textContent = 'Comparez les structures qui couvrent vos actes';
      }
    }

    function syncNoActeHint(){
      var hint = document.getElementById('sipn-mobile-no-acte-hint');
      if (!hint) return;
      var hide = selected.size > 0
        || document.body.classList.contains('sipn-has-actes')
        || document.body.classList.contains('sipn-pilier-open');
      hint.hidden = hide;
    }

    function updateSelStrip(){
      var strip = document.getElementById('sel-strip-m');
      var pills = document.getElementById('sel-pills-m');
      if (!strip || !pills) return;
      if (!selected.size) {
        strip.classList.remove('show');
        strip.hidden = true;
        syncResultsHeader();
        updateMobileFabs();
        persistSelectedActes();
        syncNoActeHint();
        return;
      }
      strip.classList.add('show');
      strip.hidden = false;
      var stripGoBtn = document.getElementById('sel-strip-go-results');
      if (stripGoBtn) {
        stripGoBtn.textContent = 'Voir les structures (' + selected.size + ') →';
      }
      pills.innerHTML = Array.from(selected).map(function(pk){
        var name = acteNames[pk] || ('Acte #' + pk);
        return '<div class="sel-pill-m">' + escapeHtml(name) +
          '<button type="button" class="sel-pill-x" data-remove-pk="' + escapeHtml(pk) + '" aria-label="Retirer"><i class="ti ti-x"></i></button></div>';
      }).join('');
      pills.querySelectorAll('[data-remove-pk]').forEach(function(btn){
        btn.addEventListener('click', function(ev){
          ev.stopPropagation();
          selected.delete(btn.getAttribute('data-remove-pk'));
          updateSelStrip();
          piliers.forEach(function(p){ updatePilierBadge(p.id); });
          if (curPilier) renderPilierPanel(curPilier, document.getElementById('pap-search-inp') ? document.getElementById('pap-search-inp').value : '');
        });
      });
      syncResultsHeader();
      updateMobileFabs();
      persistSelectedActes();
      syncNoActeHint();
    }

    function persistSelectedActes(){
      try {
        sessionStorage.setItem('sipn_selected_actes', JSON.stringify(Array.from(selected)));
        sessionStorage.setItem('sipn_acte_names', JSON.stringify(acteNames));
      } catch (e) {}
    }

    function syncResultsTab(){
      document.body.classList.toggle('sipn-has-pending-actes', selected.size > 0);
      var tab = document.querySelector('[data-mobile-tab="resultats"]');
      if (!tab) return;
      var badge = tab.querySelector('.sipn-tab-resultats-badge');
      if (selected.size > 0) {
        if (!badge) {
          badge = document.createElement('span');
          badge.className = 'sipn-tab-resultats-badge';
          tab.appendChild(badge);
        }
        badge.textContent = selected.size > 9 ? '9+' : String(selected.size);
        badge.hidden = false;
      } else if (badge) {
        badge.hidden = true;
      }
    }

    function goToSelectionResults(){
      if (!selected.size) return;
      if (window._sipnGoResultsTab) window._sipnGoResultsTab();
      else applySelectionGoResults();
    }

    function updateMobileFabs(){
      var fabClear = document.getElementById('sipn-fab-clear-actes');
      var fabGo = document.getElementById('sipn-fab-go-results');
      var fabCount = document.getElementById('sipn-fab-sel-count');
      var hasSel = selected.size > 0;
      var cartCount = window._sipnGetCartCount ? window._sipnGetCartCount() : 0;
      var onResults = document.body.classList.contains('sipn-mobile-view-results');
      var onAppView = document.body.classList.contains('sipn-mobile-view-panier')
        || document.body.classList.contains('sipn-mobile-view-messages')
        || document.body.classList.contains('sipn-mobile-view-menu');
      syncResultsTab();
      var showClear = mq.matches && hasSel && !onAppView && !(onResults && cartCount > 0);
      var showGo = showClear && !onResults;
      document.body.classList.toggle('sipn-clear-fab-visible', showClear);
      if (fabClear) {
        fabClear.hidden = !showClear;
        fabClear.classList.toggle('show', showClear);
      }
      if (fabGo) {
        fabGo.hidden = !showGo;
        fabGo.classList.toggle('show', showGo);
        var fabLabel = fabGo.querySelector('.sipn-fab-label');
        if (fabLabel) {
          fabLabel.textContent = 'Voir les structures (' + selected.size + ')';
        }
      }
      if (fabCount) {
        if (showGo && hasSel) {
          fabCount.textContent = selected.size > 9 ? '9+' : String(selected.size);
          fabCount.hidden = false;
        } else {
          fabCount.hidden = true;
        }
      }
    }

    function clearAllActes(){
      if (!selected.size) return;
      selected.clear();
      piliers.forEach(function(p){ updatePilierBadge(p.id); });
      if (curPilier) {
        renderPilierPanel(curPilier, document.getElementById('pap-search-inp') ? document.getElementById('pap-search-inp').value : '');
      }
      updateSelStrip();
      if (/[?&]acte=/.test(window.location.search)) {
        var u = new URL(window.location.href);
        u.searchParams.delete('acte');
        u.searchParams.delete('service');
        u.searchParams.delete('page');
        u.hash = '';
        var qs = u.searchParams.toString();
        window.location.href = u.pathname + (qs ? '?' + qs : '');
      }
    }

    function renderPilierPanel(pk, filter){
      var panel = document.getElementById('pilier-actes-panel');
      var pilier = piliers.find(function(p){ return p.id === pk; });
      if (!panel || !pilier) return;
      var fLow = (filter || '').toLowerCase();
      var selCount = countSelectedInPilier(pk);
      var catsHtml = '';
      (pilier.cats || []).forEach(function(cat){
        var valid = (cat.actes || []).filter(function(a){
          return !fLow || a.name.toLowerCase().indexOf(fLow) !== -1 || (cat.name || '').toLowerCase().indexOf(fLow) !== -1;
        });
        if (!valid.length) return;
        catsHtml += '<div class="pap-cat"><div class="pap-cat-lbl">' + escapeHtml(cat.name) + '</div>' +
          valid.map(function(a){
            var sel = selected.has(String(a.pk));
            return '<div class="pap-acte' + (sel ? ' sel' : '') + '" data-pap-pk="' + a.pk + '" data-pap-pilier="' + pk + '">' +
              '<input type="checkbox" class="pap-acte-chk"' + (sel ? ' checked' : '') + ' aria-label="' + escapeHtml(a.name) + '">' +
              '<span class="pap-acte-name">' + escapeHtml(a.name) + '</span>' +
              '<span class="pap-acte-cnt">' + a.count + ' struct.</span></div>';
          }).join('') + '</div>';
      });
      if (!catsHtml) catsHtml = '<div style="padding:16px;text-align:center;font-size:13px;color:#9ca3af">Aucun acte trouvé</div>';
      panel.hidden = false;
      panel.innerHTML = '<div class="pap-card"><div class="pap-head">' +
        '<div class="pap-title">' + escapeHtml(pilier.icon + ' ' + pilier.title) + '</div>' +
        '<div class="pap-sel' + (selCount > 0 ? ' show' : '') + '" id="pap-sel-count">' + selCount + ' sélectionné' + (selCount > 1 ? 's' : '') + '</div>' +
        '</div><div class="pap-search"><input type="search" id="pap-search-inp" placeholder="Filtrer les actes…" value="' + escapeHtml(filter || '') + '" autocomplete="off"></div>' +
        catsHtml + '</div>';
      panel.querySelectorAll('.pap-acte').forEach(function(row){
        row.addEventListener('click', function(){
          toggleActe(row.getAttribute('data-pap-pk'), row.getAttribute('data-pap-pilier'));
        });
      });
      var searchInp = document.getElementById('pap-search-inp');
      if (searchInp) {
        searchInp.addEventListener('input', function(){
          renderPilierPanel(pk, searchInp.value);
        });
      }
    }

    function toggleActe(pk, pilierPk){
      pk = String(pk);
      if (selected.has(pk)) selected.delete(pk);
      else selected.add(pk);
      if (pilierPk) {
        renderPilierPanel(pilierPk, document.getElementById('pap-search-inp') ? document.getElementById('pap-search-inp').value : '');
        updatePilierBadge(pilierPk);
      }
      updateSelStrip();
    }

    function scrollToActesPanel(){
      var panel = document.getElementById('pilier-actes-panel');
      if (!panel || panel.hidden) return;
      document.body.classList.add('sipn-pilier-open');
      syncNoActeHint();
      var offset = 12;
      var stickySearch = document.querySelector('.sipn-search-section');
      if (stickySearch) {
        var st = window.getComputedStyle(stickySearch);
        if (st.position === 'sticky' || st.position === 'fixed') {
          offset += stickySearch.getBoundingClientRect().height;
        }
      }
      var y = panel.getBoundingClientRect().top + window.pageYOffset - offset;
      window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
    }

    function selectPilier(pk, btnEl){
      curPilier = pk;
      gridEl.querySelectorAll('.pgrid-btn').forEach(function(b){ b.classList.remove('active'); });
      renderPilierPanel(pk, '');
      piliers.forEach(function(p){ updatePilierBadge(p.id); });
      if (btnEl) btnEl.classList.add('active');
      window.requestAnimationFrame(function(){
        window.requestAnimationFrame(scrollToActesPanel);
      });
    }

    function applySelectionGoResults(){
      if (!selected.size) return;
      var u = new URL(window.location.href);
      u.searchParams.delete('acte');
      u.searchParams.delete('service');
      u.searchParams.delete('page');
      u.hash = 'results-col';
      Array.from(selected).forEach(function(pk){ u.searchParams.append('acte', pk); });
      window.location.href = u.toString();
    }

    function renderGrid(){
      if (!mq.matches) {
        gridEl.innerHTML = '';
        return;
      }
      gridEl.innerHTML = piliers.map(function(p){
        var cnt = countSelectedInPilier(p.id);
        return '<button type="button" class="pgrid-btn" id="pbtn-' + p.id + '" data-pilier-id="' + p.id + '">' +
          '<div class="pgrid-icon">' + escapeHtml(p.icon) + '</div>' +
          '<div class="pgrid-lbl">' + escapeHtml(p.label) + '</div>' +
          '<div class="pgrid-sub">' + escapeHtml(p.sub) + '</div>' +
          '<div class="pgrid-badge' + (cnt > 0 ? ' show' : '') + '">' + cnt + '</div></button>';
      }).join('');
      gridEl.querySelectorAll('.pgrid-btn').forEach(function(btn){
        btn.addEventListener('click', function(){
          selectPilier(btn.getAttribute('data-pilier-id'), btn);
        });
        updatePilierBadge(btn.getAttribute('data-pilier-id'));
      });
    }

    var fabClearActes = document.getElementById('sipn-fab-clear-actes');
    if (fabClearActes) fabClearActes.addEventListener('click', clearAllActes);
    var stripClearActes = document.getElementById('sel-strip-clear-actes');
    if (stripClearActes) stripClearActes.addEventListener('click', clearAllActes);
    var fabGoResults = document.getElementById('sipn-fab-go-results');
    if (fabGoResults) fabGoResults.addEventListener('click', goToSelectionResults);
    var stripGoResults = document.getElementById('sel-strip-go-results');
    if (stripGoResults) stripGoResults.addEventListener('click', goToSelectionResults);
    window._sipnGoToSelectionResults = goToSelectionResults;
    window._sipnApplySelectionGoResults = applySelectionGoResults;
    window._sipnGetSelectedCount = function(){ return selected.size; };
    window._sipnGetSelectedIds = function(){ return Array.from(selected); };
    window._sipnGetActeName = function(pk){ return acteNames[String(pk)] || null; };
    window._sipnGetAllActeMap = function(){ return acteNames; };
    window._sipnAddSelectedActe = function(pk, name){
      pk = String(pk);
      if (name) acteNames[pk] = name;
      if (!selected.has(pk)) {
        selected.add(pk);
        piliers.forEach(function(p){ updatePilierBadge(p.id); });
        if (curPilier) renderPilierPanel(curPilier, document.getElementById('pap-search-inp') ? document.getElementById('pap-search-inp').value : '');
        updateSelStrip();
      }
    };
    window._sipnRemoveSelectedActe = function(pk){
      pk = String(pk);
      if (selected.has(pk)) {
        selected.delete(pk);
        piliers.forEach(function(p){ updatePilierBadge(p.id); });
        if (curPilier) renderPilierPanel(curPilier, document.getElementById('pap-search-inp') ? document.getElementById('pap-search-inp').value : '');
        updateSelStrip();
      }
    };
    window._sipnUpdateClearFab = updateMobileFabs;
    window._sipnUpdateMobileFabs = updateMobileFabs;

    renderGrid();
    updateSelStrip();
    persistSelectedActes();

    /* Auto-ouverture du pilier si ?service=ID est présent dans l'URL */
    (function autoOpenPilierFromUrl() {
      var u = new URL(window.location.href);
      var sid = u.searchParams.get('service');
      if (sid && mq.matches) {
        var btn = document.getElementById('pbtn-' + sid);
        selectPilier(sid, btn);
      } else {
        var panelInit = document.getElementById('pilier-actes-panel');
        if (panelInit) {
          panelInit.hidden = true;
          panelInit.innerHTML = '';
        }
      }
    })();

    function onMqChange(){
      mountMobileFabs();
      renderGrid();
      updateSelStrip();
      if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
      if (!mq.matches) {
        var panel = document.getElementById('pilier-actes-panel');
        if (panel) { panel.hidden = true; panel.innerHTML = ''; }
        curPilier = null;
        document.body.classList.remove('sipn-pilier-open');
      }
    }
    if (mq.addEventListener) mq.addEventListener('change', onMqChange);
    else if (mq.addListener) mq.addListener(onMqChange);
  })();

  /* ─── Onglets bottom nav ────────────────────────────────────────── */
  (function(){
    if (!document.body.classList.contains('sipn-prestations')) return;

    function bootMobileTabs(){
      var mq = window.matchMedia('(max-width: 1023px)');
      var tabBar = document.getElementById('medcare-tab-bar');
      var searchForm = document.getElementById('search-form');
      if (!tabBar || !searchForm) return;

      var tabs = {
        prestations: tabBar.querySelector('[data-mobile-tab="prestations"]'),
        resultats: tabBar.querySelector('[data-mobile-tab="resultats"]'),
        panier: tabBar.querySelector('[data-mobile-tab="panier"]'),
        messages: tabBar.querySelector('[data-mobile-tab="messages"]'),
        menu: tabBar.querySelector('[data-mobile-tab="menu"]')
      };

      function setActive(tab){
        Object.keys(tabs).forEach(function(key){
          if (!tabs[key]) return;
          tabs[key].classList.toggle('active', key === tab);
          if (key === tab) tabs[key].setAttribute('aria-current', 'page');
          else tabs[key].removeAttribute('aria-current');
        });
      }

      function clearAppViews(){
        document.body.classList.remove('sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
      }

      function closeSheets(){
        if (window._closeFilterSheet) window._closeFilterSheet();
        if (window._closeCartSheet) window._closeCartSheet();
        if (window._closeOrgPreview) window._closeOrgPreview();
        if (window._sipnClosePilierSheet) window._sipnClosePilierSheet();
        document.body.classList.remove('sipn-pilier-open');
        var papSheet = document.getElementById('sipn-pap-sheet');
        if (papSheet) {
          papSheet.classList.remove('open');
          papSheet.hidden = true;
        }
        var papBackdrop = document.getElementById('sipn-pap-backdrop');
        if (papBackdrop) {
          papBackdrop.classList.remove('open');
          papBackdrop.hidden = true;
        }
      }

      function commitActesToUrl(ids){
        if (!ids || !ids.length) return false;
        var u = new URL(window.location.href);
        u.searchParams.delete('acte');
        u.searchParams.delete('service');
        u.searchParams.delete('page');
        u.hash = 'results-col';
        ids.forEach(function(id){ u.searchParams.append('acte', String(id)); });
        window.location.assign(u.toString());
        return true;
      }

      function showResults(push){
        closeSheets();
        clearAppViews();
        var ids = window._sipnGetSelectedIds ? window._sipnGetSelectedIds() : [];
        var hasActesUrl = document.body.classList.contains('sipn-has-actes');
        var onResults = document.body.classList.contains('sipn-mobile-view-results');

        if (ids.length > 0) {
          if (onResults && hasActesUrl) {
            setActive('resultats');
            if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
            return;
          }
          if (window._sipnApplySelectionGoResults) window._sipnApplySelectionGoResults();
          else commitActesToUrl(ids);
          return;
        }
        if (!hasActesUrl) {
          if (window._sipnShowResults) window._sipnShowResults(!!push);
          else {
            document.body.classList.add('sipn-mobile-view-results');
            document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
          }
          setActive('resultats');
          window.scrollTo({ top: 0, behavior: 'smooth' });
          if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
          return;
        }

        if (window._sipnShowResults) window._sipnShowResults(!!push);
        else {
          document.body.classList.add('sipn-mobile-view-results');
          document.body.classList.remove('sipn-mobile-view-prestations');
        }
        setActive('resultats');
        if (push && history.replaceState && !window._sipnShowResults) {
          history.replaceState(null, '', window.location.pathname + window.location.search + '#results-col');
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
      }

      function showPrestations(push){
        closeSheets();
        clearAppViews();
        document.body.classList.add('sipn-mobile-view-prestations');
        document.body.classList.remove('sipn-mobile-view-results', 'sipn-mobile-view-panier', 'sipn-mobile-view-messages', 'sipn-mobile-view-menu');
        setActive('prestations');
        if (push && history.replaceState) {
          try {
            var u = new URL(window.location.href);
            u.searchParams.delete('acte');
            u.searchParams.delete('service');
            u.searchParams.delete('page');
            u.hash = '';
            history.replaceState(null, '', u.toString());
          } catch(e) {}
        }
        window.scrollTo({ top: 0, behavior: 'instant' });
        if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
      }

      function showPanier(push){
        closeSheets();
        clearAppViews();
        document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-results');
        document.body.classList.add('sipn-mobile-view-panier');
        setActive('panier');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        function afterCartSync(){
          if (window._sipnRenderCart) window._sipnRenderCart();
          if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
        }
        if (window._sipnHydrateCart) {
          window._sipnHydrateCart(afterCartSync);
        } else {
          afterCartSync();
        }
        if (push && history.replaceState) {
          history.replaceState(null, '', window.location.pathname + window.location.search + '#panier');
        }
      }

      function showMessages(push){
        closeSheets();
        clearAppViews();
        document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-results');
        document.body.classList.add('sipn-mobile-view-messages');
        setActive('messages');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (push && history.replaceState) {
          history.replaceState(null, '', window.location.pathname + window.location.search + '#messages');
        }
      }

      function showMenu(push){
        closeSheets();
        clearAppViews();
        document.body.classList.remove('sipn-mobile-view-prestations', 'sipn-mobile-view-results');
        document.body.classList.add('sipn-mobile-view-menu');
        setActive('menu');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (push && history.replaceState) {
          history.replaceState(null, '', window.location.pathname + window.location.search + '#menu');
        }
      }

      window._sipnCloseMenuView = function () {
        showPrestations(true);
      };

      function applyInitial(){
        if (!mq.matches) return;
        var hash = (window.location.hash || '').replace('#', '');
        if (hash === 'panier') { showPanier(false); return; }
        if (hash === 'messages') { showMessages(false); return; }
        if (hash === 'menu') { showMenu(false); return; }
        if (hash === 'results-col') { showResults(false); return; }
        var hasActes = document.body.classList.contains('sipn-has-actes');
        var urlResults = window.hcSearchUrlImpliesResults ? window.hcSearchUrlImpliesResults() : false;
        if (hasActes && urlResults) showResults(false);
        else showPrestations(false);
      }

      tabBar.addEventListener('click', function(e){
        if (!mq.matches) return;
        var link = e.target.closest('[data-mobile-tab], .bnav-btn');
        if (!link || !tabBar.contains(link)) return;
        var tab = link.getAttribute('data-mobile-tab');
        if (tab === 'messages' || (link.id && link.id.indexOf('messages') !== -1)) {
          window.location.href = messagingInboxUrl;
          return;
        }
        e.preventDefault();
        if (tab === 'prestations') showPrestations(true);
        else if (tab === 'resultats') showResults(true);
        else if (tab === 'panier') showPanier(true);
        else if (tab === 'menu') showMenu(true);
      });

      document.addEventListener('click', function(ev){
        if (!mq.matches || !ev.target || !ev.target.closest) return;
        var gotoPrest = ev.target.closest('.sipn-goto-prestations');
        if (gotoPrest) {
          ev.preventDefault();
          showPrestations(true);
          return;
        }
        var gotoPanier = ev.target.closest('.sipn-goto-panier, [data-sipn-goto-tab="panier"]');
        if (gotoPanier) {
          ev.preventDefault();
          showPanier(true);
          return;
        }
        var gotoMsg = ev.target.closest('.sipn-goto-messages, [data-sipn-goto-tab="messages"]');
        if (gotoMsg) {
          ev.preventDefault();
          showMessages(true);
          return;
        }
        var gotoResults = ev.target.closest('[data-sipn-goto-results]');
        if (gotoResults) {
          ev.preventDefault();
          showResults(true);
          return;
        }
        var gotoTab = ev.target.closest('[data-sipn-goto-tab]');
        if (gotoTab) {
          ev.preventDefault();
          var tab = gotoTab.getAttribute('data-sipn-goto-tab');
          if (tab === 'panier') showPanier(true);
          else if (tab === 'resultats') showResults(true);
          else if (tab === 'prestations') showPrestations(true);
        }
      });

      window.addEventListener('hashchange', applyInitial);
      if (mq.addEventListener) mq.addEventListener('change', applyInitial);
      applyInitial();
      window._sipnGoResultsTab = function(){ showResults(true); };
      window._sipnGoPrestationsTab = function(){ showPrestations(true); };
      window._sipnGoPanierTab = function(){ showPanier(true); };
      window._sipnGoMessagesTab = function(){ showMessages(true); };
      window._sipnGoMenuTab = function(){ showMenu(true); };

      var rhBack = document.getElementById('sipn-rh-back-prestations');
      if (rhBack) rhBack.addEventListener('click', function(e){ e.preventDefault(); showPrestations(true); });
      var panierBack = document.getElementById('sipn-panier-back-results');
      if (panierBack) panierBack.addEventListener('click', function(e){
        e.preventDefault();
        if (document.body.classList.contains('sipn-has-actes') || (window._sipnGetSelectedIds && window._sipnGetSelectedIds().length)) {
          showResults(true);
        } else {
          showPrestations(true);
        }
      });
      if (window._sipnUpdateMobileFabs) window._sipnUpdateMobileFabs();
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', bootMobileTabs);
    } else {
      bootMobileTabs();
    }
  })();

  /* ─── Modale Position & Géolocalisation ─────────────────────────── */
  var geoModal = $('#geo-modal'), geoBackdrop = $('#geo-backdrop'),
      latEl = $('#geo-lat'), lngEl = $('#geo-lng'), proxH = $('#geo-proximity'), chk = $('#chk-proximity'),
      sugEl = $('#geo-suggestions'), banner = $('#geo-banner'),
      bannerLabel = $('#geo-banner-label'), bannerCoords = $('#geo-banner-coords');

  function openGeo(){
    if (geoModal) geoModal.classList.add('open');
    if (geoBackdrop) geoBackdrop.classList.add('open');
    document.body.classList.add('sheet-locked');
  }
  window._sipnOpenGeo = openGeo;
  function closeGeo(){
    if (geoModal) geoModal.classList.remove('open');
    if (geoBackdrop) geoBackdrop.classList.remove('open');
    document.body.classList.remove('sheet-locked');
  }
  var btnQuickGeo = $('#btn-quick-geo');
  if (btnQuickGeo) btnQuickGeo.addEventListener('click', function(e){ e.preventDefault(); openGeo(); });
  document.addEventListener('click', function(e){
    var geoChip = e.target && e.target.closest && e.target.closest('#sipn-desktop-geo-chip');
    if (geoChip) { e.preventDefault(); e.stopPropagation(); openGeo(); }
  });
  if ($('#btn-edit-geo')) $('#btn-edit-geo').addEventListener('click', function(e){ e.preventDefault(); openGeo(); });
  if ($('#geo-modal-close')) $('#geo-modal-close').addEventListener('click', closeGeo);
  if (geoBackdrop) geoBackdrop.addEventListener('click', function(){ if (geoModal && geoModal.classList.contains('open')) closeGeo(); });

  function closeOrgPreview(){
    var op = $('#org-preview-panel'), ob = $('#org-preview-backdrop');
    if (op) op.classList.remove('open');
    if (ob) ob.classList.remove('open');
    document.body.classList.remove('sheet-locked');
  }
  function openOrgPreview(){
    var op = $('#org-preview-panel'), ob = $('#org-preview-backdrop');
    if (op) op.classList.add('open');
    if (ob) ob.classList.add('open');
    document.body.classList.add('sheet-locked');
  }
  (function(){
    var bodyEl = $('#org-preview-body');
    var closeBtn = $('#org-preview-close');
    var bd = $('#org-preview-backdrop');
    function escapeHtml(s){
      if (s == null) return '';
      var d = document.createElement('div'); d.textContent = String(s); return d.innerHTML;
    }
    function render(d){
      if (!bodyEl) return;
      var loc = [d.city, d.quartier].filter(Boolean).join(', ');
      var ins = (d.insurances || []).slice(0, 12);
      var insHtml = ins.length
        ? '<ul class="mt-1 list-disc space-y-0.5 pl-4 text-xs text-gray-600">' + ins.map(function(n){ return '<li>' + escapeHtml(n) + '</li>'; }).join('') + '</ul>'
        : '<p class="mt-1 text-xs text-gray-500">Aucune assurance déclarée sur la fiche.</p>';
      var rating = (d.avg_rating != null && d.review_count)
        ? '<p class="mt-2 text-xs text-amber-700"><span class="font-semibold">' + escapeHtml(String(d.avg_rating.toFixed(1))) + '</span>/5 · ' + escapeHtml(String(d.review_count)) + ' avis</p>'
        : '';
      var badgeDom = d.prises_sang_domicile
        ? '<span class="mt-2 inline-flex rounded-md border border-gray-200 bg-gray-50 px-2 py-0.5 text-[10px] font-medium text-gray-700">Prestations à domicile</span>'
        : '';
      var logo = d.logo_url
        ? '<img src="' + escapeHtml(d.logo_url) + '" alt="" class="h-14 w-14 shrink-0 rounded-xl border border-gray-200 object-cover">'
        : '<div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-gray-200 bg-primary-50 text-lg font-bold text-primary-600">' + escapeHtml((d.name || '?').charAt(0)) + '</div>';
      bodyEl.innerHTML =
        '<div class="flex gap-3">' + logo +
        '<div class="min-w-0 flex-1">' +
        '<div class="flex flex-wrap items-center gap-1.5">' +
        '<span class="text-base font-bold text-gray-900">' + escapeHtml(d.name) + '</span>' +
        (d.verified ? '<span class="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-semibold text-sky-800">Vérifié</span>' : '') +
        '</div>' +
        (d.type_label ? '<p class="text-xs text-gray-500">' + escapeHtml(d.type_label) + '</p>' : '') +
        (loc ? '<p class="mt-1 text-xs text-gray-600"><i class="ti ti-map-pin"></i> ' + escapeHtml(loc) + '</p>' : '') +
        rating + badgeDom +
        '<p class="mt-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Assurances acceptées</p>' + insHtml +
        '<p class="mt-3 text-xs text-gray-500">' + escapeHtml(String(d.actes_count || 0)) + ' acte(s) au catalogue</p>' +
        '<a href="' + escapeHtml(d.fiche_url) + '" class="btn-primary mt-4 inline-flex w-full items-center justify-center rounded-xl py-3 text-center text-sm font-bold">Ouvrir la fiche complète</a>' +
        '</div></div>';
    }
    function load(slug){
      if (!bodyEl) return;
      bodyEl.innerHTML = '<p class="text-gray-500">Chargement…</p>';
      openOrgPreview();
      var url = previewUrlTpl.replace('org-preview-slug-tmp', encodeURIComponent(slug));
      fetch(url, {credentials:'same-origin'})
        .then(function(r){ if (!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
        .then(render)
        .catch(function(){ bodyEl.innerHTML = '<p class="text-red-600">Impossible de charger cette structure.</p>'; });
    }
    document.addEventListener('click', function(ev){
      var t = ev.target;
      if (!t || !t.closest) return;
      var btn = t.closest('.org-preview-trigger');
      if (!btn) return;
      var slug = btn.getAttribute('data-org-slug');
      if (!slug) return;
      ev.preventDefault();
      load(slug);
    });
    if (closeBtn) closeBtn.addEventListener('click', closeOrgPreview);
    if (bd) bd.addEventListener('click', closeOrgPreview);
    window._closeOrgPreview = closeOrgPreview;
  })();

  document.addEventListener('keydown', function(e){
    if (e.key !== 'Escape') return;
    var profilModal = document.getElementById('profil-struct-modal');
    if (profilModal && profilModal.style.display === 'flex') {
      if (window.closeProfilStruct) window.closeProfilStruct();
      e.preventDefault();
      return;
    }
    var op = $('#org-preview-panel');
    if (op && op.classList.contains('open')) { closeOrgPreview(); e.preventDefault(); return; }
    if (geoModal && geoModal.classList.contains('open')) { closeGeo(); e.preventDefault(); return; }
    if (window._closeFilterSheet) window._closeFilterSheet();
  });

  function syncProximity(){ if(proxH&&chk) proxH.value = chk.checked?'1':'0'; }
  if (chk){
    chk.addEventListener('change', function(){
      syncProximity();
      var sf = document.getElementById('search-form');
      if (sf) sf.submit();
    });
    syncProximity();
  }

  function setCoords(lat,lng,enableProximity){
    if(latEl) latEl.value = lat;
    if(lngEl) lngEl.value = lng;
    if(enableProximity && chk){ chk.checked = true; syncProximity(); }
    var sb = $('#btn-save-profile'); if (sb) sb.disabled = !lat||!lng;
    if (banner){
      banner.style.display = (lat && lng) ? 'flex' : 'none';
      if (bannerCoords) bannerCoords.textContent = lat + ', ' + lng;
      if (bannerLabel) bannerLabel.textContent = 'Position détectée';
      reverseLookup(lat, lng);
    }
    var sfGeo = document.getElementById('search-form');
    if (sfGeo) sfGeo.submit();
  }
  window.setCoords = setCoords;

  function reverseLookup(lat, lng){
    fetch(apiReverseUrl + '?lat=' + encodeURIComponent(lat) + '&lon=' + encodeURIComponent(lng))
      .then(function(r){return r.json();})
      .then(function(d){
        if (d && d.result && d.result.display_name && bannerLabel) {
          var parts = d.result.display_name.split(',').slice(0,3).join(',');
          bannerLabel.textContent = parts;
        }
      }).catch(function(){});
  }

  /* Reverse-lookup au chargement si position déjà fournie */
  if (latEl && lngEl && latEl.value && lngEl.value) reverseLookup(latEl.value, lngEl.value);

  var bg = $('#btn-geolocate');
  if (bg) bg.addEventListener('click', function(){
    var w = $('#geo-http-warn');
    if (w) w.classList.add('hidden');

    if (!navigator.geolocation){
      if (location.protocol === 'http:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        if (w) w.classList.remove('hidden');
      } else {
        alert('Géolocalisation indisponible sur cet appareil.');
      }
      return;
    }
    bg.disabled = true; bg.textContent = 'Localisation…';
    navigator.geolocation.getCurrentPosition(function(p){
      setCoords(p.coords.latitude.toFixed(6), p.coords.longitude.toFixed(6), true);
      bg.disabled = false; bg.innerHTML = '<span><i class="ti ti-antenna"></i></span> Utiliser ma position GPS';
    }, function(err){
      bg.disabled = false; bg.innerHTML = '<span><i class="ti ti-antenna"></i></span> Utiliser ma position GPS';
      if (location.protocol === 'http:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        if (w) w.classList.remove('hidden');
        return;
      }
      var msg = 'Position refusée ou indisponible.';
      if (err) {
        if (err.code === 1) msg = 'Autorisation GPS refusée. Activez la localisation dans les réglages de votre navigateur.';
        else if (err.code === 2) msg = 'Position GPS momentanément indisponible.';
        else if (err.code === 3) msg = 'Délai GPS dépassé. Veuillez réessayer ou entrer une adresse.';
      }
      alert(msg);
    }, {enableHighAccuracy:true, timeout:15000});
  });

  var bn = $('#btn-geocode');
  var geoInput = $('#geo-address-q');
  if (geoInput && bn) {
    geoInput.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        bn.click();
      }
    });
  }
  if (bn) bn.addEventListener('click', function(){
    var q = $('#geo-address-q') ? $('#geo-address-q').value.trim() : '';
    if (q.length < 2) return;
    bn.disabled = true; bn.textContent = '…';
    fetch(apiGeocodeUrl + '?q=' + encodeURIComponent(q))
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (!sugEl) return;
        sugEl.innerHTML = '';
        if (!d.results || !d.results.length){ sugEl.classList.add('hidden'); return; }
        d.results.forEach(function(it){
          var li = document.createElement('li');
          li.className = 'cursor-pointer border-b border-gray-100 px-3 py-2 last:border-0 hover:bg-accent-50';
          li.textContent = it.display_name;
          li.addEventListener('click', function(){
            setCoords(String(it.lat), String(it.lon), true);
            sugEl.classList.add('hidden');
          });
          sugEl.appendChild(li);
        });
        sugEl.classList.remove('hidden');
      }).finally(function(){ bn.disabled = false; bn.textContent = 'Chercher'; });
  });

  var sb = $('#btn-save-profile');
  if (sb) sb.addEventListener('click', function(){
    var fd = new FormData();
    fd.append('csrfmiddlewaretoken', getCsrfToken());
    fd.append('lat', latEl.value); fd.append('lng', lngEl.value); fd.append('ajax', '1');
    fetch(saveSearchLocationUrl, {
      method: 'POST',
      headers: {'X-CSRFToken': getCsrfToken()},
      credentials: 'same-origin',
      body: fd
    })
      .then(function(r){ return r.json(); })
      .then(function(d){ if (d.ok) window.location.reload(); else alert(d.error || 'Erreur'); })
      .catch(function(){ alert('Erreur réseau.'); });
  });

})();

