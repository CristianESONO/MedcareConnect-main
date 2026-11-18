/**
 * search-mobile-filters.js — Bottom sheets filtres mobile (Tri, Assurance, Zone, Budget, Délai)
 * Extrait de search.html — Phase 2 refacto MedCare
 */
(function initSipnMobileFilterSheets() {
  'use strict';

  var sheet = document.getElementById('sipn-m-sheet');
  var overlay = document.getElementById('sipn-m-sheet-overlay');
  var bodyEl = document.getElementById('sipn-m-sheet-body');
  var titleEl = document.getElementById('sipn-m-sheet-title');
  var btnApply = document.getElementById('sipn-m-sheet-apply');
  var footerEl = sheet && sheet.querySelector('.sipn-m-sheet-footer');
  var form = document.getElementById('search-form');
  if (!sheet || !overlay || !bodyEl || !form) return;

  var metaEl = document.getElementById('sipn-m-filter-meta');
  var meta = {};
  try { meta = JSON.parse(metaEl ? metaEl.textContent : '{}'); } catch (e) { meta = {}; }

  var PMIN = parseFloat(meta.priceMinGlobal) || 0;
  var PMAX = parseFloat(meta.priceMaxGlobal) || 500000;
  var curType = null;
  var pending = {
    sort: meta.sort || 'price_asc',
    assurances: (meta.assurances || []).slice(),
    city: meta.city || '',
    delai: meta.delai || '',
    priceMax: meta.priceMax || ''
  };

  var SORT_OPTS = [
    { val: 'price_asc', lbl: 'Prix croissant' },
    { val: 'price_desc', lbl: 'Prix décroissant' },
    { val: 'popular', lbl: 'Couverture assurance' },
    { val: 'delai_asc', lbl: 'Délai le plus court' },
    { val: 'name_org', lbl: 'Zone / Quartier' }
  ];

  function isMobileFilter() { return window.matchMedia('(max-width: 1023px)').matches; }
  function esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function fmtF(n) { return Math.round(Number(n || 0)).toLocaleString('fr-FR'); }

  function openSheet() {
    overlay.hidden = false;
    sheet.hidden = false;
    requestAnimationFrame(function () {
      overlay.classList.add('open');
      sheet.classList.add('open');
    });
  }
  function closeSheet() {
    overlay.classList.remove('open');
    sheet.classList.remove('open');
    curType = null;
    setTimeout(function () {
      overlay.hidden = true;
      sheet.hidden = true;
    }, 280);
  }

  function syncAssuranceToForm() {
    var center = document.getElementById('id-assurance-dem-center');
    var vals = pending.assurances.slice();
    if (center) {
      if (window.jQuery && jQuery.fn.select2 && jQuery(center).data('select2')) {
        jQuery(center).val(vals).trigger('change');
      } else {
        Array.from(center.options).forEach(function (o) { o.selected = vals.indexOf(o.value) !== -1; });
      }
    }
    var form2 = document.getElementById('search-form');
    if (form2) {
      form2.querySelectorAll('input[name="assurance"].dem-sync-hidden').forEach(function (n) { n.remove(); });
      vals.forEach(function (v) {
        var h = document.createElement('input');
        h.type = 'hidden'; h.name = 'assurance'; h.value = v; h.className = 'dem-sync-hidden';
        form2.appendChild(h);
      });
    }
  }

  function getLiveMeta() {
    var metaEl = document.getElementById('sipn-m-filter-meta');
    try {
      if (metaEl && metaEl.textContent) return JSON.parse(metaEl.textContent);
    } catch (e) { }
    return meta;
  }

  function syncPendingFromCurrentInputs() {
    var lm = getLiveMeta();
    var cityInp = document.getElementById('sipn-filter-city') || document.querySelector('input[name="city"]');
    var delaiSel = document.getElementById('sipn-filter-delai') || document.querySelector('select[name="delai"]');
    var sortSel = document.getElementById('id-sort-dem') || document.querySelector('select[name="sort"]');
    var priceMaxInp = document.getElementById('sipn-inp-price-max') || document.querySelector('input[name="price_max"]');

    if (cityInp && cityInp.value !== undefined) pending.city = cityInp.value;
    else if (lm.city !== undefined) pending.city = lm.city;

    if (delaiSel && delaiSel.value !== undefined) pending.delai = delaiSel.value;
    else if (lm.delai !== undefined) pending.delai = lm.delai;

    if (sortSel && sortSel.value !== undefined) pending.sort = sortSel.value;
    else if (lm.sort !== undefined) pending.sort = lm.sort;

    if (priceMaxInp && priceMaxInp.value !== undefined) pending.priceMax = priceMaxInp.value;
    else if (lm.priceMax !== undefined) pending.priceMax = lm.priceMax;

    if (Array.isArray(lm.assurances)) pending.assurances = lm.assurances.slice();
  }

  function submitFilters() {
    var form = document.getElementById('search-form');
    if (!form) return;

    var sortSel = document.getElementById('id-sort-dem');
    if (sortSel) sortSel.value = pending.sort;
    var sortAll = form.querySelectorAll('select[name="sort"]');
    sortAll.forEach(function (s) { s.value = pending.sort; });

    var cityInp = document.getElementById('sipn-filter-city');
    if (cityInp) cityInp.value = pending.city;
    var cityAll = form.querySelectorAll('input[name="city"]');
    cityAll.forEach(function (i) { i.value = pending.city; });

    var delaiSel = document.getElementById('sipn-filter-delai');
    if (delaiSel) delaiSel.value = pending.delai;
    var delaiAll = form.querySelectorAll('select[name="delai"]');
    delaiAll.forEach(function (s) { s.value = pending.delai; });

    var priceMaxInp = document.getElementById('sipn-inp-price-max');
    if (priceMaxInp) priceMaxInp.value = pending.priceMax;
    var priceMaxAll = form.querySelectorAll('input[name="price_max"]');
    priceMaxAll.forEach(function (i) { i.value = pending.priceMax; });

    syncAssuranceToForm();
    closeSheet();
    form.submit();
  }

  function renderSortSheet() {
    if (titleEl) titleEl.textContent = 'Trier les résultats';
    if (footerEl) footerEl.style.display = 'none';
    bodyEl.innerHTML = SORT_OPTS.map(function (o) {
      return '<button type="button" class="sipn-m-sheet-opt" data-sipn-sort-val="' + esc(o.val) + '">' + esc(o.lbl) + '</button>';
    }).join('');
    bodyEl.querySelectorAll('[data-sipn-sort-val]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        pending.sort = btn.getAttribute('data-sipn-sort-val');
        var lbl = document.getElementById('sipn-m-sort-lbl');
        if (lbl) lbl.textContent = btn.textContent.trim();
        var chip = document.getElementById('sipn-m-sort-chip');
        if (chip) { chip.classList.add('active'); chip.setAttribute('aria-pressed', 'true'); }
        submitFilters();
      });
    });
  }

  function renderAssuranceSheet() {
    if (titleEl) titleEl.textContent = 'Filtrer par assurance';
    if (footerEl) footerEl.style.display = '';
    var tpl = document.getElementById('sipn-m-tpl-assurance');
    bodyEl.innerHTML = tpl ? tpl.innerHTML : '<p class="sipn-m-sheet-empty">Aucune assurance disponible.</p>';
    bodyEl.querySelectorAll('.sipn-m-ins-cb').forEach(function (cb) {
      cb.checked = pending.assurances.indexOf(cb.value) !== -1;
    });
  }

  function renderZoneSheet() {
    if (titleEl) titleEl.textContent = 'Zone / Quartier';
    if (footerEl) footerEl.style.display = '';
    var liveMeta = getLiveMeta();
    var rawZones = (liveMeta && Array.isArray(liveMeta.zones) && liveMeta.zones.length) ? liveMeta.zones : (meta.zones || []);
    if (!rawZones.length) {
      var datalist = document.getElementById('city-options');
      if (datalist) {
        Array.from(datalist.options).forEach(function (opt) {
          var val = (opt.value || '').trim();
          if (val && rawZones.indexOf(val) === -1) rawZones.push(val);
        });
      }
    }
    var zones = [''].concat(rawZones);
    bodyEl.innerHTML = '<div class="sipn-m-sheet-radios">' + zones.map(function (z) {
      var lbl = z ? z : 'Toutes les zones';
      var checked = (pending.city || '') === z ? ' checked' : '';
      return '<label class="sipn-m-ins-opt"><input type="radio" name="sipn-m-zone" value="' + esc(z) + '"' + checked + '><span>' + esc(lbl) + '</span></label>';
    }).join('') + '</div>';
    bodyEl.querySelectorAll('input[name="sipn-m-zone"]').forEach(function (r) {
      r.addEventListener('change', function () { pending.city = r.value; });
    });
  }

  function renderBudgetSheet() {
    if (titleEl) titleEl.textContent = 'Budget maximum';
    if (footerEl) footerEl.style.display = '';
    var cur = pending.priceMax ? parseFloat(pending.priceMax) : PMAX;
    if (isNaN(cur)) cur = PMAX;
    cur = Math.min(Math.max(cur, PMIN || 5000), PMAX);
    bodyEl.innerHTML =
      '<div class="sipn-m-budget-wrap">' +
      '<div class="sipn-m-budget-display" id="sipn-m-budget-display">' +
      (cur >= PMAX ? 'Sans limite' : fmtF(cur) + ' FCFA max') +
      '</div>' +
      '<input type="range" id="sipn-m-budget-range" class="sipn-m-budget-range" min="' + (PMIN || 5000) + '" max="' + PMAX + '" step="1000" value="' + cur + '">' +
      '<div class="sipn-m-budget-hints"><span>' + fmtF(PMIN || 5000) + ' F</span><span>Sans limite</span></div>' +
      '</div>';
    var rng = document.getElementById('sipn-m-budget-range');
    var disp = document.getElementById('sipn-m-budget-display');
    rng.addEventListener('input', function () {
      var hi = parseFloat(rng.value);
      pending.priceMax = hi >= PMAX ? '' : String(Math.round(hi));
      if (disp) disp.textContent = hi >= PMAX ? 'Sans limite' : fmtF(hi) + ' FCFA max';
    });
  }

  function renderDelaiSheet() {
    if (titleEl) titleEl.textContent = 'Délai de résultats';
    if (footerEl) footerEl.style.display = '';
    var liveMeta = getLiveMeta();
    var rawChoices = (liveMeta && Array.isArray(liveMeta.delaiChoices) && liveMeta.delaiChoices.length) ? liveMeta.delaiChoices : (meta.delaiChoices || []);
    if (!rawChoices.length) {
      var sel = document.getElementById('sipn-filter-delai') || document.querySelector('select[name="delai"]');
      if (sel) {
        Array.from(sel.options).forEach(function (opt) {
          var val = (opt.value || '').trim();
          var lbl = (opt.textContent || '').trim();
          if (val && !rawChoices.some(function (c) { return c.val === val; })) {
            rawChoices.push({ val: val, lbl: lbl });
          }
        });
      }
    }
    var choices = [{ val: '', lbl: 'Tous les délais' }].concat(rawChoices);
    bodyEl.innerHTML = '<div class="sipn-m-sheet-radios">' + choices.map(function (o) {
      var checked = pending.delai === o.val ? ' checked' : '';
      return '<label class="sipn-m-ins-opt"><input type="radio" name="sipn-m-delai" value="' + esc(o.val) + '"' + checked + '><span>' + esc(o.lbl) + '</span></label>';
    }).join('') + '</div>';
    bodyEl.querySelectorAll('input[name="sipn-m-delai"]').forEach(function (r) {
      r.addEventListener('change', function () { pending.delai = r.value; });
    });
  }

  function openFilterSheet(type) {
    syncPendingFromCurrentInputs();
    curType = type;
    if (type === 'sort') renderSortSheet();
    else if (type === 'assurance') renderAssuranceSheet();
    else if (type === 'zone') renderZoneSheet();
    else if (type === 'budget') renderBudgetSheet();
    else if (type === 'delai') renderDelaiSheet();
    else return;
    openSheet();
  }

  /* Délégation globale sur document pour que les chips mobile restent toujours cliquables après mise à jour AJAX */
  document.addEventListener('click', function (e) {
    var chip = e.target && e.target.closest && e.target.closest('[data-sipn-m-sheet]');
    if (!chip) return;
    e.preventDefault();
    e.stopPropagation();
    if (!isMobileFilter()) return;
    var type = chip.getAttribute('data-sipn-m-sheet');
    if (type) openFilterSheet(type);
  });

  if (btnApply) {
    btnApply.addEventListener('click', function () {
      if (curType === 'sort') return;
      if (curType === 'assurance') {
        pending.assurances = Array.from(bodyEl.querySelectorAll('.sipn-m-ins-cb:checked')).map(function (c) { return c.value; });
        var n = pending.assurances.length;
        var lbl = document.getElementById('sipn-m-ins-lbl');
        var chip = document.getElementById('sipn-m-ins-chip');
        if (lbl) lbl.textContent = n ? n + ' assurance' + (n > 1 ? 's filtrées' : ' filtrée') : 'Assurance';
        if (chip) {
          chip.classList.toggle('active', n > 0);
          chip.setAttribute('aria-pressed', n > 0 ? 'true' : 'false');
        }
      }
      if (curType === 'zone') {
        var zr = bodyEl.querySelector('input[name="sipn-m-zone"]:checked');
        pending.city = zr ? zr.value : '';
        var zlbl = document.getElementById('sipn-m-zone-lbl');
        var zchip = document.getElementById('sipn-m-zone-chip');
        if (zlbl) zlbl.innerHTML = '<i class="ti ti-map-pin"></i> ' + (pending.city ? esc(pending.city) : 'Zone');
        if (zchip) {
          zchip.classList.toggle('active', !!pending.city);
          zchip.setAttribute('aria-pressed', pending.city ? 'true' : 'false');
        }
      }
      if (curType === 'delai') {
        var dr = bodyEl.querySelector('input[name="sipn-m-delai"]:checked');
        pending.delai = dr ? dr.value : '';
        var dlbl = document.getElementById('sipn-m-delai-lbl');
        var dchip = document.getElementById('sipn-m-delai-chip');
        if (dlbl && dr) {
          var dl = dr.closest('label');
          var txt = pending.delai ? (dl ? dl.querySelector('span').textContent : 'Délai') : 'Délai';
          dlbl.innerHTML = '<i class="ti ti-clock"></i> ' + esc(txt);
        }
        if (dchip) {
          dchip.classList.toggle('active', !!pending.delai);
          dchip.setAttribute('aria-pressed', pending.delai ? 'true' : 'false');
        }
      }
      if (curType === 'budget') {
        var bchip = document.getElementById('sipn-m-budget-chip');
        var blbl = document.getElementById('sipn-m-budget-lbl');
        if (blbl) blbl.textContent = pending.priceMax ? '≤ ' + fmtF(pending.priceMax) + ' F' : 'Budget';
        if (bchip) {
          bchip.classList.toggle('active', !!pending.priceMax);
          bchip.setAttribute('aria-pressed', pending.priceMax ? 'true' : 'false');
        }
      }
      submitFilters();
    });
  }

  overlay.addEventListener('click', closeSheet);
})();

