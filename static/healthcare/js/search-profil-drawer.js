/**
 * MedCare - Search Profile Drawer
 * Gère le volet latéral / tiroir de profil complet d'un établissement médical :
 * - Chargement dynamique du profil de la structure
 * - Filtrage interne des actes du profil
 * - Popover des horaires & liste des assurances
 * - Calcul d'itinéraire / Google Maps avec géolocalisation
 * - Ajout / Retrait d'actes et redirection devis
 */
(function initProfilDrawer() {
  'use strict';

  var cfg = window.SIPN_CONFIG || {};
  var urls = cfg.urls || {};
  var drawerUrlTpl = urls.drawerUrlTpl || '/structure/0/drawer/';
  var cartDevisBaseUrl = urls.cartDevisBaseUrl || '/panier/devis/';
  var cartViewUrl = urls.cartViewUrl || '/panier/';
  var loginUrl = urls.login || '/connexion/';
  var userIsAuthed = !!cfg.userIsAuthenticated;

  window.toggleHorairesPop = function() {
    var pop = document.getElementById('horaires-pop');
    if (!pop) return;
    pop.hidden = !pop.hidden;
  };

  window.toggleAssurDrop = function() {
    var list = document.getElementById('assur-list');
    var caret = document.getElementById('assur-caret');
    if (!list) return;
    list.hidden = !list.hidden;
    if (caret) caret.textContent = list.hidden ? '▼' : '▲';
  };

  window.filterProfilActes = function(q) {
    q = (q || '').trim().toLowerCase();
    document.querySelectorAll('#profil-struct-modal .pa-row').forEach(function(row) {
      var nom = row.getAttribute('data-nom') || '';
      row.style.display = (!q || nom.indexOf(q) !== -1) ? '' : 'none';
    });
    document.querySelectorAll('#profil-struct-modal .pa-cat').forEach(function(cat) {
      var visible = Array.prototype.some.call(cat.querySelectorAll('.pa-row'), function(row) {
        return row.style.display !== 'none';
      });
      cat.style.display = visible ? '' : 'none';
    });
  };

  window.openMapsUrl = function(button) {
    var mapsUrl = button ? button.getAttribute('data-maps-url') : '';
    var dest = '';
    if (mapsUrl && mapsUrl !== '#') {
      try {
        var u = new URL(mapsUrl);
        dest = u.searchParams.get('destination') || '';
      } catch (e) {
        dest = mapsUrl;
      }
    }
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        function(pos) {
          var lat = pos.coords.latitude;
          var lng = pos.coords.longitude;
          var dirUrl = 'https://www.google.com/maps/dir/?api=1&origin=' + lat + ',' + lng + '&destination=' + encodeURIComponent(dest || mapsUrl);
          window.open(dirUrl, '_blank');
        },
        function() {
          var dirUrl = mapsUrl || ('https://www.google.com/maps/dir/?api=1&origin=&destination=' + encodeURIComponent(dest));
          window.open(dirUrl, '_blank');
        },
        { timeout: 4000, enableHighAccuracy: true }
      );
    } else {
      var dirUrl = mapsUrl || ('https://www.google.com/maps/dir/?api=1&origin=&destination=' + encodeURIComponent(dest));
      window.open(dirUrl, '_blank');
    }
  };

  function profilDrawerUrl(structId) {
    var url = drawerUrlTpl.replace('/0/', '/' + encodeURIComponent(String(structId)) + '/');
    try {
      var built = new URL(url, window.location.origin);
      new URLSearchParams(window.location.search).forEach(function(val, key) {
        if (key === 'assurance') built.searchParams.append(key, val);
      });
      return built.toString();
    } catch (e) {
      return url;
    }
  }

  function goProfilDevis(orgId) {
    if (window.closeProfilStruct) window.closeProfilStruct();
    var devisTarget = orgId
      ? (cartDevisBaseUrl + '?org=' + encodeURIComponent(String(orgId)))
      : (cartDevisBaseUrl || cartViewUrl);
    if (userIsAuthed) {
      window.location.href = devisTarget;
      return;
    }
    window.location.href = loginUrl + '?next=' + encodeURIComponent(devisTarget);
  }

  window.closeProfilStruct = function() {
    var modal = document.getElementById('profil-struct-modal');
    var overlay = document.getElementById('profil-struct-overlay');
    if (modal) {
      modal.style.display = 'none';
      modal.removeAttribute('data-org-id');
    }
    if (overlay) overlay.style.display = 'none';
    document.body.style.overflow = '';
    if (window._sipnRenderCart) window._sipnRenderCart();
  };

  function loadProfilDrawerContent(structId, modal) {
    fetch(profilDrawerUrl(structId), { credentials: 'same-origin' })
      .then(function(response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.text();
      })
      .then(function(html) {
        modal.innerHTML = html;
        modal.scrollTop = 0;
        var searchInp = document.getElementById('profil-acte-search');
        if (searchInp) {
          searchInp.addEventListener('input', function() {
            window.filterProfilActes(searchInp.value);
          });
        }
        if (window._sipnSyncProfilDrawer) window._sipnSyncProfilDrawer();
        if (window.initTrajetConfig) {
          window.initTrajetConfig(structId);
          if (window.curActe && window.focusTrajetActe) {
            setTimeout(function() {
              window.focusTrajetActe(window.curActe, structId);
            }, 80);
          }
        }
      })
      .catch(function(error) {
        console.error('Error loading profile:', error);
        modal.innerHTML = '<div style="padding:24px;color:#dc2626;font-size:13px">Impossible de charger ce profil.</div>';
      });
  }

  window.openProfilStruct = function(structId) {
    var modal = document.getElementById('profil-struct-modal');
    var overlay = document.getElementById('profil-struct-overlay');
    if (!modal || !overlay || !structId) return;

    modal.setAttribute('data-org-id', String(structId));
    modal.style.display = 'flex';
    overlay.style.display = 'block';
    document.body.style.overflow = 'hidden';
    modal.innerHTML = '<div style="padding:24px;color:#6b7280;font-size:13px">Chargement…</div>';

    if (window._sipnHydrateCart) {
      window._sipnHydrateCart(function() {
        loadProfilDrawerContent(structId, modal);
      });
    } else {
      loadProfilDrawerContent(structId, modal);
    }
  };

  var overlay = document.getElementById('profil-struct-overlay');
  if (overlay) overlay.addEventListener('click', window.closeProfilStruct);

  document.addEventListener('click', function(e) {
    var t = e.target;
    if (!t || !t.closest) return;

    var profilBtn = t.closest('.profil-drawer-trigger');
    if (profilBtn) {
      e.preventDefault();
      e.stopPropagation();
      var orgId = profilBtn.getAttribute('data-org-id');
      if (orgId) window.openProfilStruct(orgId);
      return;
    }

    var modal = document.getElementById('profil-struct-modal');
    if (!modal || modal.style.display !== 'flex') return;

    if (t.closest('[data-profil-devis]')) {
      e.preventDefault();
      goProfilDevis(t.closest('[data-profil-devis]').getAttribute('data-org-id'));
      return;
    }

    if (t.closest('[data-profil-clear-org]')) {
      e.preventDefault();
      var clearOrg = t.closest('[data-profil-clear-org]').getAttribute('data-profil-clear-org');
      if (!clearOrg || !window._sipnTogglePaFromElement) return;
      var toRemove = [];
      document.querySelectorAll('#profil-struct-modal .profil-pa-row.in-cart[data-pa-id]').forEach(function(row) {
        if (String(row.getAttribute('data-pa-org-id')) === String(clearOrg)) {
          toRemove.push(row);
        }
      });
      toRemove.forEach(function(row) { window._sipnTogglePaFromElement(row); });
      return;
    }

    if (t.closest('[data-profil-focus-rdv]')) {
      e.preventDefault();
      var recap = document.getElementById('profil-panier-recap');
      if (recap) recap.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    var paRow = t.closest('#profil-struct-modal .profil-pa-row');
    if (paRow) {
      if (paRow.getAttribute('data-ambulance-acte') === '1') return;
      if (t.closest('.ai-check')) {
        e.preventDefault();
        e.stopPropagation();
      } else {
        e.preventDefault();
      }
      if (window._sipnTogglePaFromElement) window._sipnTogglePaFromElement(paRow);
    }
  });

  document.addEventListener('keydown', function(e) {
    var row = e.target && e.target.closest ? e.target.closest('#profil-struct-modal .profil-pa-row') : null;
    if (!row || row.getAttribute('data-ambulance-acte') === '1') return;
    if (e.key !== 'Enter' && e.key !== ' ') return;
    e.preventDefault();
    if (window._sipnTogglePaFromElement) window._sipnTogglePaFromElement(row);
  });

  var cartDevisBtn = document.getElementById('dem-cart-devis-btn');
  if (cartDevisBtn) {
    cartDevisBtn.addEventListener('click', function(e) {
      e.preventDefault();
      goProfilDevis(cartDevisBtn.getAttribute('data-devis-org-id'));
    });
  }
})();

