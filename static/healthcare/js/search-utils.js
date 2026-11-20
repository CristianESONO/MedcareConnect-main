/**
 * search-utils.js — Utilitaires partagés + init Select2
 * Extrait de search.html — Phase 2 refacto MedCare
 *
 * Expose via window.SIPN :
 *   getCsrfToken(), getCookie(name), filterActeTree(inp, tree)
 *
 * Dépendances : jQuery, Select2 (chargés avant ce fichier)
 */
(function (w) {
  'use strict';

  /* ─── Helpers ──────────────────────────────────────────────────── */
  function getCookie(name) {
    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m[2]) : '';
  }

  /** Jeton CSRF : champ caché (base.html) — le cookie est HttpOnly en HTTPS. */
  function getCsrfToken() {
    var inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (inp && inp.value) return inp.value;
    return getCookie('csrftoken') || '';
  }

  /* ─── Select2 ──────────────────────────────────────────────────── */
  jQuery(function ($) {
    $('.s2-single, .s2-single-mob').select2({ placeholder: '— choisir —', allowClear: true, width: '100%' });
    $('.s2-multi, .s2-multi-mob').not('.s2-multi-dem-bar').select2({ placeholder: 'Sélectionner…', allowClear: true, width: '100%', closeOnSelect: false });
    var $form = $('#search-form');
    if ($form.length) {
      var s2t = null;
      $('.s2-multi, .s2-multi-mob').not('.s2-multi-dem-bar').on('select2:select select2:unselect select2:clear', function () {
        if (w.__suppressAutoFilterSubmit) return;
        clearTimeout(s2t);
        s2t = setTimeout(function () { $form[0].submit(); }, 400);
      });
    }
  });

  /* ─── Filtre local « Parcourir les actes » (piliers Déméthior) ─── */
  function filterActeTree(inp, tree) {
    if (!inp || !tree) return;
    inp.addEventListener('input', function () {
      var q = (inp.value || '').trim().toLowerCase();
      tree.querySelectorAll('[data-dem-acte-group]').forEach(function (grp) {
        var rows = grp.querySelectorAll('[data-dem-acte-name]');
        var nvis = 0;
        rows.forEach(function (row) {
          var nm = row.getAttribute('data-dem-acte-name') || '';
          var show = !q || nm.indexOf(q) !== -1;
          row.style.display = show ? '' : 'none';
          if (show) nvis++;
        });
        grp.querySelectorAll('[data-dem-acte-subgroup]').forEach(function (subgroup) {
          var subgroupRows = subgroup.querySelectorAll('[data-dem-acte-name]');
          var hasVisibleRows = Array.prototype.some.call(subgroupRows, function (row) {
            return row.style.display !== 'none';
          });
          subgroup.style.display = (!q || hasVisibleRows) ? '' : 'none';
          subgroup.open = q
            ? hasVisibleRows
            : subgroup.getAttribute('data-default-open') === '1';
        });
        var vis = (!q || nvis > 0);
        grp.style.display = vis ? '' : 'none';
        if (grp.tagName === 'DETAILS') {
          grp.open = q
            ? nvis > 0
            : grp.getAttribute('data-default-open') === '1';
        }
      });
    });
  }

  /* Connexion filtre → arbre mode embed no-wrap (sidebar desktop) */
  (function () {
    var navInp = document.getElementById('nav-search-input');
    var navTree = document.getElementById('nav-tree');
    if (navInp && navTree) filterActeTree(navInp, navTree);
  })();

  /* Connexion filtre → arbre modes classiques (.dem-acte-browse) */
  Array.prototype.slice.call(document.querySelectorAll('.dem-acte-browse')).forEach(function (browse) {
    var inp = browse.querySelector('.dem-acte-filter-input');
    var tree = browse.querySelector('.dem-acte-tree');
    filterActeTree(inp, tree);
  });

  /* ─── Expose globalement ─────────────────────────────────────── */
  w.SIPNUtils = {
    getCookie: getCookie,
    getCsrfToken: getCsrfToken,
    filterActeTree: filterActeTree,
  };

}(window));

