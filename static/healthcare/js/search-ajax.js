/**
 * search-ajax.js — Navigation AJAX piliers/actes + configurateur ambulance
 * Extrait de search.html — Phase 2 refacto MedCare
 *
 * Dépend de : window.SIPN_CONFIG (injecté dans search.html)
 *   SIPN_CONFIG.urls.search
 *   SIPN_CONFIG.urls.login
 *   SIPN_CONFIG.urls.ambulanceTrajetDevis
 *   SIPN_CONFIG.userIsAuthenticated
 */
(function () {
  'use strict';

  /* ─── AJAX Navigation for Pillars and Acts (no page refresh) ─ */
  (function () {
    if (!document.body.classList.contains('sipn-prestations')) return;

    function updatePageContent(url) {
      /* Indicateur de chargement visible */
      var resultsWrap = document.querySelector('.sipn-results-desktop-wrap') || document.getElementById('results-col');
      if (resultsWrap) {
        resultsWrap.style.opacity = '0.5';
        resultsWrap.style.pointerEvents = 'none';
      }
      fetch(url, {
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-Fetch-Mode': 'partial'
        }
      })
        .then(function (response) {
          if (!response.ok) throw new Error('Network response was not ok');
          return response.text();
        })
        .then(function (html) {
          var parser = new DOMParser();
          var doc = parser.parseFromString(html, 'text/html');

          /* Mise à jour du sidebar (liste actes + compteurs) */
          var newSidebar = doc.getElementById('sidebar-desktop');
          var oldSidebar = document.getElementById('sidebar-desktop');
          if (newSidebar && oldSidebar) oldSidebar.innerHTML = newSidebar.innerHTML;

          /* Mise à jour de la colonne résultats desktop */
          var newResults = doc.querySelector('.sipn-results-desktop-wrap');
          var oldResults = document.querySelector('.sipn-results-desktop-wrap');
          if (newResults && oldResults) {
            oldResults.innerHTML = newResults.innerHTML;
            oldResults.style.opacity = '';
            oldResults.style.pointerEvents = '';
          } else if (oldResults) {
            oldResults.style.opacity = '';
            oldResults.style.pointerEvents = '';
          }

          /* Mise à jour colonne résultats (results-col) si sipn-results-desktop-wrap absent */
          var newResultsCol = doc.getElementById('results-col');
          var oldResultsCol = document.getElementById('results-col');
          if (newResultsCol && oldResultsCol && !oldResults) {
            oldResultsCol.innerHTML = newResultsCol.innerHTML;
          }

          /* Mise à jour des résultats mobile */
          var newMobileResults = doc.querySelector('.sipn-mobile-results-view');
          var oldMobileResults = document.querySelector('.sipn-mobile-results-view');
          if (newMobileResults && oldMobileResults) oldMobileResults.innerHTML = newMobileResults.innerHTML;

          /* Mise à jour du bandeau de sélection mobile (#sel-strip-m) */
          var newSelStrip = doc.getElementById('sel-strip-m');
          var oldSelStrip = document.getElementById('sel-strip-m');
          if (newSelStrip && oldSelStrip) {
            oldSelStrip.innerHTML = newSelStrip.innerHTML;
            oldSelStrip.hidden = newSelStrip.hidden;
            oldSelStrip.className = newSelStrip.className;
          }

          /* Mise à jour de la barre de filtres desktop (#sipn-desktop-filter-row) */
          var newFilterRow = doc.getElementById('sipn-desktop-filter-row');
          var oldFilterRow = document.getElementById('sipn-desktop-filter-row');
          if (newFilterRow && oldFilterRow) oldFilterRow.innerHTML = newFilterRow.innerHTML;

          /* Mise à jour de la datalist des zones (#city-options) */
          var newCityOpts = doc.getElementById('city-options');
          var oldCityOpts = document.getElementById('city-options');
          if (newCityOpts && oldCityOpts) oldCityOpts.innerHTML = newCityOpts.innerHTML;

          /* Mise à jour des métadonnées filtres mobile (#sipn-m-filter-meta) */
          var newMetaEl = doc.getElementById('sipn-m-filter-meta');
          var oldMetaEl = document.getElementById('sipn-m-filter-meta');
          if (newMetaEl && oldMetaEl) oldMetaEl.textContent = newMetaEl.textContent;

          if (resultsWrap) {
            resultsWrap.style.opacity = '';
            resultsWrap.style.pointerEvents = '';
          }

          /* Mise à jour des hidden inputs acte dans search-form */
          var formEl = document.getElementById('search-form');
          if (formEl) {
            formEl.querySelectorAll('input[name="acte"]').forEach(function (inp) { inp.remove(); });
            var newActeInputs = doc.querySelectorAll('#search-form input[name="acte"]');
            newActeInputs.forEach(function (inp) {
              var clone = document.createElement('input');
              clone.type = 'hidden';
              clone.name = 'acte';
              clone.value = inp.value;
              formEl.appendChild(clone);
            });
          }

          /* Mettre à jour l'URL seulement si ce n'est pas déjà fait */
          if (window.location.href !== url) history.pushState({}, '', url);

          /* Synchroniser les body classes depuis la réponse AJAX */
          var newBodyClasses = doc.body.className ? doc.body.className.split(/\s+/) : [];
          var sipnPrefixes = ['sipn-prestations', 'sipn-has-actes'];
          sipnPrefixes.forEach(function (cls) {
            if (newBodyClasses.indexOf(cls) !== -1) document.body.classList.add(cls);
            else document.body.classList.remove(cls);
          });

          /* Recalculer la vue mobile après mise à jour des classes */
          if (window._sipnShowResults && window._sipnShowPrestations) {
            var hasActesNow = document.body.classList.contains('sipn-has-actes');
            var sp = new URLSearchParams(url.split('?')[1] || '');
            var urlHasActe = sp.has('acte') || (sp.get('q') || '').trim().length >= 2;
            if (hasActesNow && urlHasActe) window._sipnShowResults(false);
            else if (!hasActesNow) window._sipnShowPrestations(false);
          }

          /* Réinitialiser les event listeners pour le nouveau contenu */
          reinitActeMultiSelect();
          if (window.closeDemFilterDropdown) window.closeDemFilterDropdown();
          if (window._sipnHydrateCart) {
            window._sipnHydrateCart(function () {
              if (window._sipnSyncCartCardStates) window._sipnSyncCartCardStates();
              if (window._sipnCheckMissingCart) window._sipnCheckMissingCart();
            });
          } else if (window._sipnSyncCartCardStates) {
            window._sipnSyncCartCardStates();
          }
        })
        .catch(function (error) {
          console.error('AJAX navigation error:', error);
          if (resultsWrap) {
            resultsWrap.style.opacity = '';
            resultsWrap.style.pointerEvents = '';
          }
          /* Fallback : rechargement classique */
          window.location.href = url;
        });
    }
    window.updatePageContent = updatePageContent;

    function reinitActeMultiSelect() {
      var sf = document.getElementById('search-form');
      var ids = sf
        ? Array.from(sf.querySelectorAll('input[name="acte"]')).map(function (i) { return String(i.value); })
        : (new URLSearchParams(window.location.search)).getAll('acte');
      document.querySelectorAll('.dem-acte-row--multi').forEach(function (row) {
        var pk = row.getAttribute('data-dem-acte-pk');
        var isActive = ids.indexOf(String(pk)) !== -1;
        row.classList.toggle('active', isActive);
        var chk = row.querySelector('.dem-acte-chk');
        if (chk) chk.checked = isActive;
      });
      if (ids.length > 0) showResultsArea();
      else hideResultsArea();
    }

    /* Intercept pillar clicks */
    document.addEventListener('click', function (e) {
      var pillarBtn = e.target.closest('.dem-pbtn');
      if (pillarBtn) {
        e.preventDefault();
        e.stopPropagation();
        if (pillarBtn.classList.contains('active')) return;
        var url = pillarBtn.getAttribute('href');
        if (url) {
          hideResultsArea();
          updatePageContent(url);
        }
      }
    });

    function hideResultsArea() {
      var resultsMobile = document.querySelector('.sipn-mobile-results-view');
      if (resultsMobile && window.innerWidth < 1024) resultsMobile.style.display = 'none';
      var resultsDesktop = document.querySelector('.sipn-results-desktop-wrap');
      if (resultsDesktop) resultsDesktop.style.display = '';
    }

    function showResultsArea() {
      var resultsDesktop = document.querySelector('.sipn-results-desktop-wrap');
      var resultsMobile = document.querySelector('.sipn-mobile-results-view');
      if (resultsDesktop) resultsDesktop.style.display = '';
      if (resultsMobile) resultsMobile.style.display = '';
    }

    function checkAndToggleResults() {
      var ids = new URL(window.location.href).searchParams.getAll('acte');
      if (ids.length > 0) showResultsArea();
      else hideResultsArea();
    }

    showResultsArea();

    /* ─── Ambulance Trajet Configurator ───────────────────────── */
    var TRAJET_DATA = {};
    var TRAJET_STATE = null;
    var curActe = null;

    function initAmbulanceTrajetConfig() {
      document.querySelectorAll('.trajet-config-container').forEach(function (container) {
        var orgId = container.getAttribute('data-org-id');
        if (orgId) {
          TRAJET_DATA[orgId] = {
            distance_defaut: 10, tarif_km: 500, tarif_escale: 2000,
            tarif_km_long: 800, suppl_aerien: 50000, tarif_heure: 8000, tarif_soignant: 15000,
            actes: {
              'Ambulance simple': { flow: 'trajet', base: 10000, medic: 'Chauffeur ambulancier' },
              'Ambulance médicalisée avec infirmier': { flow: 'trajet', base: 25000, medic: 'Infirmier à bord' },
              'Ambulance médicalisée avec médecin': { flow: 'trajet', base: 45000, medic: 'Médecin à bord', urgence: true },
              'Transport réanimatoire': { flow: 'trajet', base: 90000, medic: 'Équipe de réanimation', urgence: true },
              'Rapatriement national': { flow: 'rapatriement', base: 200000, scope: 'national' },
              'Rapatriement international': { flow: 'rapatriement', base: 500000, scope: 'international', surDevis: true },
              'Couverture événement': { flow: 'evenement', base: 50000, evt: 'Événement sportif/culturel' }
            }
          };
        }
      });
    }

    function resolveTrajetActe(structId, candidate) {
      var sId = String(structId);
      var cfg = TRAJET_DATA[sId] || TRAJET_DATA[structId];
      if (!cfg || !cfg.actes) return 'Ambulance simple';
      var keys = Object.keys(cfg.actes);
      if (candidate && cfg.actes[candidate]) return candidate;
      var resolvedName = (typeof getActeName === 'function' ? getActeName(candidate) : '') || String(candidate || '');
      var low = resolvedName.toLowerCase();
      if (low) {
        for (var i = 0; i < keys.length; i++) {
          var k = keys[i];
          if (k.toLowerCase().includes(low) || low.includes(k.toLowerCase())) return k;
        }
        if (low.includes('rapatriement') || low.includes('évacuation') || low.includes('evacuation')) {
          var rMatch = keys.find(function (k) { return cfg.actes[k].flow === 'rapatriement'; });
          if (rMatch) return rMatch;
        }
        if (low.includes('couverture') || low.includes('événement') || low.includes('evenement') || low.includes('assistance') || low.includes('manifestation') || low.includes('sportive')) {
          var cMatch = keys.find(function (k) { return cfg.actes[k].flow === 'evenement'; });
          if (cMatch) return cMatch;
        }
      }
      var urlParams = new URLSearchParams(window.location.search);
      var q = (urlParams.get('q') || '').toLowerCase();
      var serv = (urlParams.get('service') || '').toLowerCase();
      if (q.includes('rapatriement') || q.includes('évacuation') || q.includes('evacuation') || serv.includes('rapatriement')) {
        return keys.find(function (k) { return cfg.actes[k].flow === 'rapatriement'; }) || keys[0];
      }
      if (q.includes('couverture') || q.includes('événement') || q.includes('evenement') || q.includes('assistance') || q.includes('manifestation') || q.includes('sportive') || serv.includes('couverture')) {
        return keys.find(function (k) { return cfg.actes[k].flow === 'evenement'; }) || keys[0];
      }
      return keys[0];
    }

    function initTrajetConfig(structId) {
      if (!structId) return;
      var sId = String(structId);
      if (!TRAJET_DATA[sId]) {
        TRAJET_DATA[sId] = {
          distance_defaut: 10, tarif_km: 600, tarif_escale: 3000, tarif_km_long: 450,
          suppl_aerien: 400000, tarif_heure: 15000, tarif_soignant: 25000,
          actes: {
            'Ambulance simple': { flow: 'trajet', base: 10000, medic: 'Chauffeur ambulancier' },
            'Ambulance médicalisée avec infirmier': { flow: 'trajet', base: 25000, medic: 'Infirmier à bord' },
            'Ambulance médicalisée avec médecin': { flow: 'trajet', base: 45000, medic: 'Médecin à bord', urgence: true },
            'Transport réanimatoire': { flow: 'trajet', base: 90000, medic: 'Équipe de réanimation', urgence: true },
            'Évacuation sanitaire': { flow: 'trajet', base: 120000, medic: 'Équipe médicalisée', urgence: true },
            'Rapatriement national': { flow: 'rapatriement', base: 200000, scope: 'national' },
            'Rapatriement international': { flow: 'rapatriement', base: 0, scope: 'international', surDevis: true },
            'Couverture médicale sportive': { flow: 'evenement', base: 75000, evt: 'Événement sportif' },
            'Couverture médicale de manifestation publique': { flow: 'evenement', base: 90000, evt: 'Manifestation publique' },
            'Assistance médicale sur site': { flow: 'evenement', base: 60000, evt: 'Assistance sur site' }
          }
        };
      }
      TRAJET_DATA[structId] = TRAJET_DATA[sId];
      var cfg = TRAJET_DATA[sId];
      if (!cfg) return;
      var startActe = resolveTrajetActe(sId, curActe);
      TRAJET_STATE = {
        structId: sId, acte: startActe,
        depart: '', etapes: [], arrivee: '', allerRetour: false, distance: cfg.distance_defaut,
        villeDep: '', paysDep: 'Sénégal', villeArr: '', paysArr: '', mode: 'routier', dateR: '', etatPatient: 'Stable, allongé', accompagnant: false,
        lieu: '', dateE: '', duree: 6, effectif: 500, equipe: { infirmier: true, medecin: false, ambulance: true, poste: false },
        nuit: false
      };
      renderTrajetConfig();
    }

    function acteCfg() {
      var sId = String(TRAJET_STATE.structId);
      var cfg = TRAJET_DATA[sId] || TRAJET_DATA[TRAJET_STATE.structId];
      return cfg.actes[TRAJET_STATE.acte] || cfg.actes[Object.keys(cfg.actes)[0]];
    }

    function computeTrajet() {
      var st = TRAJET_STATE, sId = String(st.structId), cfg = TRAJET_DATA[sId] || TRAJET_DATA[st.structId], ac = acteCfg();
      var nuit = st.nuit ? 8000 : 0;
      if (ac.flow === 'trajet') {
        var km = st.allerRetour ? st.distance * 2 : st.distance;
        var coutKm = Math.round(km * cfg.tarif_km);
        var coutEscales = st.etapes.length * cfg.tarif_escale;
        return { flow: 'trajet', surDevis: false, km: km, base: ac.base, coutKm: coutKm, coutEscales: coutEscales, nuit: nuit, total: ac.base + coutKm + coutEscales + nuit };
      }
      if (ac.flow === 'rapatriement') {
        if (ac.surDevis) return { flow: 'rapatriement', surDevis: true, total: null };
        var coutKm2 = Math.round(st.distance * cfg.tarif_km_long);
        var aerien = st.mode === 'aérien' ? cfg.suppl_aerien : 0;
        return { flow: 'rapatriement', surDevis: false, km: st.distance, base: ac.base, coutKm: coutKm2, aerien: aerien, nuit: nuit, total: ac.base + coutKm2 + aerien + nuit };
      }
      var coutHeures = Math.round(st.duree * cfg.tarif_heure);
      var extra = (st.equipe.medecin ? 1 : 0) + (st.equipe.poste ? 1 : 0);
      var coutEquipe = extra * cfg.tarif_soignant;
      var majEffectif = st.effectif > 2000 ? 100000 : (st.effectif > 1000 ? 50000 : 0);
      return { flow: 'evenement', surDevis: false, base: ac.base, coutHeures: coutHeures, coutEquipe: coutEquipe, majEffectif: majEffectif, total: ac.base + coutHeures + coutEquipe + majEffectif };
    }

    function useMyLocation(target, idx) {
      var label = '<i class="ti ti-map-pin"></i> Ma position GPS (Dakar)';
      if (target === 'depart') TRAJET_STATE.depart = label;
      else if (target === 'arrivee') TRAJET_STATE.arrivee = label;
      else if (target === 'lieu') TRAJET_STATE.lieu = label;
      else if (target === 'etape') TRAJET_STATE.etapes[idx] = label;
      renderTrajetConfig();
    }

    function addrField(ph, value, onin, locTarget, locIdx) {
      return '<div style="display:flex;gap:6px;align-items:center">' +
        '<input type="text" placeholder="' + ph + '" value="' + (value || '').replace(/"/g, '&quot;') + '" ' +
        'oninput="' + onin + ';updateTrajetRecap()" style="flex:1;font-size:11px;padding:7px 9px;border:1.5px solid var(--blue-m);border-radius:7px;background:#fff">' +
        '<button onclick="useMyLocation(\'' + locTarget + '\'' + (locIdx !== undefined ? ',' + locIdx : '') + ')" title="Utiliser ma position" ' +
        'style="background:var(--blue-l);border:1.5px solid var(--blue-m);border-radius:7px;padding:7px 9px;cursor:pointer;font-size:12px;color:var(--blue)"><i class="ti ti-map-pin"></i></button></div>';
    }

    function fLabel(t) { return '<label style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--g600)">' + t + '</label>'; }
    function txtField(ph, value, onin) { return '<input type="text" placeholder="' + ph + '" value="' + (value || '').replace(/"/g, '&quot;') + '" oninput="' + onin + ';updateTrajetRecap()" style="width:100%;font-size:11px;padding:7px 9px;border:1.5px solid var(--blue-m);border-radius:7px;background:#fff;box-sizing:border-box">'; }
    function numField(value, onin, min) { return '<input type="number" min="' + (min || 0) + '" value="' + value + '" oninput="' + onin + ';updateTrajetRecap()" style="width:120px;font-size:11px;padding:6px 9px;border:1.5px solid var(--g200);border-radius:7px;background:#fff">'; }

    function renderTrajetConfig() {
      if (!TRAJET_STATE) return;
      var sId = String(TRAJET_STATE.structId);
      var contentId = 'trajet-config-content-' + sId;
      var wrap = document.getElementById(contentId);
      if (!wrap) { var compWrap = document.getElementById('trajet-config-comp-' + curActe); if (compWrap) wrap = compWrap; }
      if (!wrap) return;
      var st = TRAJET_STATE;
      var cfg = TRAJET_DATA[sId] || TRAJET_DATA[st.structId];
      if (!cfg || !cfg.actes) return;
      var ac = acteCfg();
      var acteNames = Object.keys(cfg.actes);
      var titleByFlow = { trajet: '<i class="ti ti-ambulance"></i> Composez votre trajet', rapatriement: '<i class="ti ti-world"></i> Détails du rapatriement', evenement: '<i class="ti ti-stethoscope"></i> Détails de la couverture médicale' };
      var body = '';
      if (ac.flow === 'trajet') body = flowTrajet(st, ac);
      else if (ac.flow === 'rapatriement') body = flowRapatriement(st, ac);
      else body = flowEvenement(st, cfg, ac);
      wrap.innerHTML =
        '<div style="background:var(--blue-l,#e8f4fb);border:1.5px solid var(--blue-m,#bfdbfe);border-radius:9px;padding:12px 14px;margin-bottom:12px">' +
        '<div style="font-size:12px;font-weight:800;color:var(--blue,#0a5c8a);margin-bottom:8px">' + titleByFlow[ac.flow] + '</div>' +
        fLabel('Service demandé') +
        '<select onchange="TRAJET_STATE.acte=this.value;renderTrajetConfig()" style="width:100%;font-size:11px;padding:7px 9px;border:1.5px solid var(--blue,#0a5c8a);border-radius:7px;margin:3px 0 6px;background:#fff;font-weight:600;color:#1f2937">' +
        acteNames.map(function (n) { return '<option value="' + n + '"' + (n === st.acte ? ' selected' : '') + '>' + n + '</option>'; }).join('') +
        '</select>' +
        (ac.medic ? '<div style="font-size:10px;color:var(--blue,#0a5c8a);margin-bottom:10px;font-weight:600"><i class="ti ti-stethoscope"></i> ' + ac.medic + (ac.urgence ? ' · <i class="ti ti-bolt"></i> prise en charge d\'urgence' : '') + '</div>' : '<div style="margin-bottom:8px"></div>') +
        body +
        '<div id="trajet-recap-' + sId + '"></div>' +
        '<button onclick="obtenirDevisTrajet()" style="width:100%;margin-top:10px;background:#25d366;color:#fff;border:none;border-radius:9px;padding:11px;font-size:12px;font-weight:700;cursor:pointer;font-family:DM Sans,sans-serif"><i class="ti ti-message"></i> Obtenir mon devis</button>' +
        '<div style="font-size:8px;color:var(--g400,#9ca3af);margin-top:6px;line-height:1.5">Estimation indicative. Le devis final vous sera confirmé par la structure après vérification des informations.</div>' +
        '</div>';
      updateTrajetRecap();
    }

    function flowTrajet(st, ac) {
      return fLabel('<i class="ti ti-map-pin"></i> Point de départ') +
        '<div style="margin:3px 0 8px">' + addrField('Adresse de départ...', st.depart, 'TRAJET_STATE.depart=this.value', 'depart') + '</div>' +
        st.etapes.map(function (e, i) {
          return fLabel('<i class="ti ti-circle-stop"></i> Étape ' + (i + 1)) +
            '<div style="display:flex;gap:6px;align-items:center;margin:3px 0 8px">' +
            '<div style="flex:1">' + addrField('Adresse de l\'étape...', e, 'TRAJET_STATE.etapes[' + i + ']=this.value', 'etape', i) + '</div>' +
            '<button onclick="removeEtape(' + i + ')" style="background:var(--red-l,#fde8e8);border:none;border-radius:7px;width:32px;height:32px;cursor:pointer;font-size:12px;color:var(--red,#c0392b);flex-shrink:0"><i class="ti ti-x"></i></button></div>';
        }).join('') +
        '<button onclick="addEtape()" style="font-size:10px;background:#fff;color:var(--blue);border:1.5px dashed var(--blue-m);border-radius:7px;padding:6px 10px;cursor:pointer;margin-bottom:10px;font-family:DM Sans,sans-serif">+ Ajouter une étape sur le trajet</button>' +
        fLabel('<i class="ti ti-flag"></i> Point d\'arrivée') +
        '<div style="margin:3px 0 8px">' + addrField('Adresse d\'arrivée...', st.arrivee, 'TRAJET_STATE.arrivee=this.value', 'arrivee') + '</div>' +
        '<label style="display:flex;align-items:center;gap:8px;font-size:11px;cursor:pointer;margin-bottom:10px"><input type="checkbox"' + (st.allerRetour ? ' checked' : '') + ' onchange="TRAJET_STATE.allerRetour=this.checked;updateTrajetRecap()"> <i class="ti ti-repeat"></i> Retour au point de départ (aller-retour)</label>' +
        fLabel('Distance estimée (km)') +
        '<div style="display:flex;align-items:center;gap:8px;margin:3px 0 10px">' + numField(st.distance, 'TRAJET_STATE.distance=parseFloat(this.value)||0', 0) + '<span style="font-size:9px;color:var(--g400)"><i class="ti ti-satellite"></i> Calculée par GPS en production</span></div>' +
        supplNuit(st);
    }

    function flowRapatriement(st, ac) {
      var intl = ac.scope === 'international';
      return '<div style="display:grid;grid-template-columns:' + (intl ? '1fr 1fr' : '1fr') + ';gap:8px;margin-bottom:8px">' +
        '<div>' + fLabel('Ville de départ') + txtField('Ex : Dakar', st.villeDep, 'TRAJET_STATE.villeDep=this.value') + '</div>' +
        (intl ? '<div>' + fLabel('Pays de départ') + txtField('Ex : Sénégal', st.paysDep, 'TRAJET_STATE.paysDep=this.value') + '</div>' : '') +
        '</div>' +
        '<div style="display:grid;grid-template-columns:' + (intl ? '1fr 1fr' : '1fr') + ';gap:8px;margin-bottom:8px">' +
        '<div>' + fLabel('Ville d\'arrivée') + txtField('Ex : ' + (intl ? 'Paris' : 'Saint-Louis'), st.villeArr, 'TRAJET_STATE.villeArr=this.value') + '</div>' +
        (intl ? '<div>' + fLabel('Pays d\'arrivée') + txtField('Ex : France', st.paysArr, 'TRAJET_STATE.paysArr=this.value') + '</div>' : '') +
        '</div>' +
        fLabel('Mode de transport') +
        '<div style="display:flex;gap:6px;margin:3px 0 8px">' +
        modePill('routier', '<i class="ti ti-ambulance"></i> Routier', st) + modePill('aérien', '<i class="ti ti-plane"></i> Aérien', st) +
        '</div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">' +
        '<div>' + fLabel('Date souhaitée') + '<input type="date" value="' + st.dateR + '" onchange="TRAJET_STATE.dateR=this.value;updateTrajetRecap()" style="width:100%;font-size:11px;padding:6px 9px;border:1.5px solid var(--blue-m);border-radius:7px;background:#fff;box-sizing:border-box"></div>' +
        '<div>' + fLabel('État du patient') + '<select onchange="TRAJET_STATE.etatPatient=this.value;updateTrajetRecap()" style="width:100%;font-size:11px;padding:6px 9px;border:1.5px solid var(--blue-m);border-radius:7px;background:#fff">' +
        ['Stable, allongé', 'Sous oxygène', 'Soins intensifs / ventilé', 'Isolé (contagieux)'].map(function (o) { return '<option' + (o === st.etatPatient ? ' selected' : '') + '>' + o + '</option>'; }).join('') +
        '</select></div></div>' +
        '<label style="display:flex;align-items:center;gap:8px;font-size:11px;cursor:pointer;margin-bottom:8px"><input type="checkbox"' + (st.accompagnant ? ' checked' : '') + ' onchange="TRAJET_STATE.accompagnant=this.checked;updateTrajetRecap()"> <i class="ti ti-users"></i> Présence d\'un accompagnant</label>' +
        (intl ? '<div style="font-size:9px;color:var(--g600);background:#fff;border:1px solid var(--g100);border-radius:7px;padding:6px 9px;margin-bottom:8px"><i class="ti ti-file-text"></i> Documents requis : passeport, autorisation médicale de vol, coordination avec l\'assurance. Devis personnalisé selon destination.</div>' :
          fLabel('Distance estimée (km)') + '<div style="display:flex;align-items:center;gap:8px;margin:3px 0 8px">' + numField(st.distance, 'TRAJET_STATE.distance=parseFloat(this.value)||0', 0) + '<span style="font-size:9px;color:var(--g400)"><i class="ti ti-satellite"></i> Calculée par GPS en production</span></div>') +
        supplNuit(st);
    }

    function modePill(m, txt, st) {
      return '<button onclick="TRAJET_STATE.mode=\'' + m + '\';renderTrajetConfig()" style="flex:1;font-size:11px;font-weight:600;padding:7px;border-radius:7px;cursor:pointer;border:1.5px solid ' +
        (st.mode === m ? 'var(--blue);background:var(--blue);color:#fff' : 'var(--blue-m);background:#fff;color:var(--blue)') + '">' + txt + '</button>';
    }

    function flowEvenement(st, cfg, ac) {
      var eq = function (cle, txt) {
        return '<label style="display:flex;align-items:center;gap:5px;font-size:10px;background:#fff;border:1.5px solid var(--g200);border-radius:7px;padding:4px 9px;cursor:pointer"><input type="checkbox"' + (st.equipe[cle] ? ' checked' : '') + ' onchange="TRAJET_STATE.equipe.' + cle + '=this.checked;updateTrajetRecap()"> ' + txt + '</label>';
      };
      return '<div style="font-size:10px;color:var(--blue);margin-bottom:8px"><i class="ti ti-clipboard-list"></i> Type : ' + ac.evt + '</div>' +
        fLabel('<i class="ti ti-map-pin"></i> Lieu / site de l\'évènement') +
        '<div style="margin:3px 0 8px">' + addrField('Adresse du site...', st.lieu, 'TRAJET_STATE.lieu=this.value', 'lieu') + '</div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">' +
        '<div>' + fLabel('Date') + '<input type="date" value="' + st.dateE + '" onchange="TRAJET_STATE.dateE=this.value;updateTrajetRecap()" style="width:100%;font-size:11px;padding:6px 9px;border:1.5px solid var(--blue-m);border-radius:7px;background:#fff;box-sizing:border-box"></div>' +
        '<div>' + fLabel('Durée (heures)') + numField(st.duree, 'TRAJET_STATE.duree=parseFloat(this.value)||0', 1) + '</div>' +
        '</div>' +
        fLabel('Effectif attendu (personnes)') +
        '<div style="margin:3px 0 8px">' + numField(st.effectif, 'TRAJET_STATE.effectif=parseInt(this.value)||0', 0) + '</div>' +
        fLabel('Dispositif médical souhaité') +
        '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 8px">' +
        eq('infirmier', 'Infirmier') + eq('medecin', 'Médecin') + eq('ambulance', 'Ambulance sur place') + eq('poste', 'Poste de secours') +
        '</div>' +
        supplNuit(st);
    }

    function supplNuit(st) {
      return '<label style="display:flex;align-items:center;gap:8px;font-size:11px;cursor:pointer;margin-bottom:4px"><input type="checkbox"' + (st.nuit ? ' checked' : '') + ' onchange="TRAJET_STATE.nuit=this.checked;updateTrajetRecap()"> <i class="ti ti-moon"></i> Intervention de nuit / week-end (+8 000 F)</label>';
    }

    function addEtape() { TRAJET_STATE.etapes.push(''); renderTrajetConfig(); }
    function removeEtape(idx) { TRAJET_STATE.etapes.splice(idx, 1); renderTrajetConfig(); }
    function money(n) { return n.toLocaleString('fr-FR') + ' F'; }

    function recapLine(label, val, strong) {
      return '<div style="display:flex;justify-content:space-between;font-size:11px;padding:3px 0"><span style="color:var(--g600)">' + label + '</span><span style="' + (strong ? 'font-weight:800;color:var(--green-d)' : 'font-weight:600;color:var(--text)') + '">' + val + '</span></div>';
    }

    function updateTrajetRecap() {
      if (!TRAJET_STATE) return;
      var box = document.getElementById('trajet-recap-' + TRAJET_STATE.structId);
      if (!box) return;
      var st = TRAJET_STATE, cfg = TRAJET_DATA[st.structId], ac = acteCfg();
      var r = computeTrajet();
      var itin = '', lines = '';
      if (r.flow === 'trajet') {
        var pts = [{ r: 'Départ', v: st.depart || '(à définir)' }].concat(st.etapes.map(function (e, i) { return { r: 'Étape ' + (i + 1), v: e || '(à définir)' }; })).concat([{ r: 'Arrivée', v: st.arrivee || '(à définir)' }]);
        if (st.allerRetour) pts.push({ r: 'Retour', v: st.depart || '(point de départ)' });
        itin = '<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--g400);margin-bottom:4px">Itinéraire · ' + r.km + ' km' + (st.allerRetour ? ' (aller-retour)' : '') + '</div>' +
          pts.map(function (p) { return '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">' + p.r + ' :</span> ' + p.v + '</div>'; }).join('');
        lines = recapLine('Prix de base (' + st.acte + ')', money(r.base)) +
          recapLine('Distance (' + r.km + ' km × ' + money(cfg.tarif_km) + ')', money(r.coutKm)) +
          (st.etapes.length ? recapLine(st.etapes.length + ' étape' + (st.etapes.length > 1 ? 's' : '') + ' × ' + money(cfg.tarif_escale), money(r.coutEscales)) : '') +
          (r.nuit ? recapLine('Nuit / week-end', money(r.nuit)) : '');
      } else if (r.flow === 'rapatriement') {
        itin = '<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--g400);margin-bottom:4px">Rapatriement ' + (ac.scope === 'international' ? 'international' : 'national') + '</div>' +
          '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">De :</span> ' + (st.villeDep || '(à définir)') + (ac.scope === 'international' ? ', ' + (st.paysDep || 'Sénégal') : '') + '</div>' +
          '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">À :</span> ' + (st.villeArr || '(à définir)') + (ac.scope === 'international' ? ', ' + (st.paysArr || '(à définir)') : '') + '</div>' +
          '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">Mode :</span> ' + (st.mode === 'aérien' ? '<i class="ti ti-plane"></i> Aérien' : '<i class="ti ti-ambulance"></i> Routier') + '</div>';
        lines = recapLine('Prix de base', money(r.base)) +
          recapLine('Distance (' + r.km + ' km × ' + money(cfg.tarif_km_long) + ')', money(r.coutKm)) +
          (r.aerien ? recapLine('Supplément aérien', money(r.aerien)) : '') +
          (r.nuit ? recapLine('Nuit / week-end', money(r.nuit)) : '');
      } else {
        itin = '<div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--g400);margin-bottom:4px">Couverture médicale</div>' +
          '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">Lieu :</span> ' + (st.lieu || '(à définir)') + '</div>' +
          '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">Date :</span> ' + (st.dateE || '(à définir)') + ' · Durée : ' + st.duree + 'h</div>' +
          '<div style="font-size:10px;color:var(--g600);padding:1px 0"><span style="color:var(--g400)">Effectif :</span> ' + st.effectif + ' personnes</div>';
        lines = recapLine('Prix de base', money(r.base)) +
          recapLine('Durée (' + st.duree + 'h × ' + money(cfg.tarif_heure) + ')', money(r.coutHeures)) +
          (r.coutEquipe ? recapLine('Équipe médicale', money(r.coutEquipe)) : '') +
          (r.majEffectif ? recapLine('Majoration effectif', money(r.majEffectif)) : '') +
          (r.nuit ? recapLine('Nuit / week-end', money(r.nuit)) : '');
      }
      box.innerHTML = itin + '<div style="margin-top:8px">' + lines + '</div>' +
        (r.surDevis ? '<div style="font-size:10px;color:var(--g600);background:#fff;border:1px solid var(--g100);border-radius:7px;padding:6px 9px;margin-top:8px"><i class="ti ti-clipboard-list"></i> Ce service nécessite un devis personnalisé. Contactez la structure pour une estimation précise.</div>' :
          '<div style="display:flex;justify-content:space-between;font-size:11px;padding:6px 0;border-top:1px solid var(--g200);margin-top:6px"><span style="font-weight:700;color:var(--g600)">Total estimé</span><span style="font-extrabold;color:var(--green-d)">' + money(r.total) + '</span></div>');
    }

    function trajetToast(msg, level) {
      if (window._sipnToast) window._sipnToast(msg, level);
      else if (window.MedcareUI && typeof MedcareUI.toast === 'function') MedcareUI.toast(msg, { level: level || 'info' });
      else alert(msg);
    }

    function obtenirDevisTrajet() {
      if (!TRAJET_STATE) { trajetToast('Configurez d\'abord votre trajet.', 'warning'); return; }
      var st = TRAJET_STATE;
      var r = computeTrajet();
      var lines = [], configParts = [];
      if (r.flow === 'trajet') {
        var resume = (st.depart || 'Départ') + ' → ' + (st.arrivee || 'Arrivée') + ' · ' + r.km + ' km' + (st.allerRetour ? ' (A/R)' : '');
        configParts.push(resume);
        lines.push({ nom: st.acte + ' · ' + resume, price: r.base });
        lines.push({ nom: 'Distance ' + r.km + ' km', price: r.coutKm });
        if (r.coutEscales) lines.push({ nom: st.etapes.length + ' étape(s)', price: r.coutEscales });
        if (r.nuit) lines.push({ nom: 'Nuit / week-end', price: r.nuit });
      } else if (r.flow === 'rapatriement') {
        var rapResume = (st.villeDep || 'Départ') + ' → ' + (st.villeArr || 'Arrivée') + ' · ' + st.mode + ' · ' + st.etatPatient;
        configParts.push(rapResume);
        if (r.surDevis) { lines.push({ nom: st.acte + ' · ' + rapResume, price: 0 }); }
        else {
          lines.push({ nom: st.acte + ' · ' + rapResume, price: r.base });
          lines.push({ nom: 'Distance ' + r.km + ' km', price: r.coutKm });
          if (r.aerien) lines.push({ nom: 'Supplément aérien', price: r.aerien });
          if (r.nuit) lines.push({ nom: 'Nuit / week-end', price: r.nuit });
        }
      } else {
        var dispo = Object.keys(st.equipe).filter(function (k) { return st.equipe[k]; }).join(', ');
        var evtResume = (st.lieu || 'Site') + ' · ' + (st.dateE || 'date à définir') + ' · ' + st.duree + 'h · ' + st.effectif + ' pers.';
        configParts.push(evtResume + (dispo ? ' · ' + dispo : ''));
        lines.push({ nom: st.acte + ' · ' + evtResume, price: r.base });
        lines.push({ nom: 'Présence ' + st.duree + 'h', price: r.coutHeures });
        if (r.coutEquipe) lines.push({ nom: 'Renfort équipe médicale', price: r.coutEquipe });
        if (r.majEffectif) lines.push({ nom: 'Majoration grand public', price: r.majEffectif });
      }

      /* ── Variables Django injectées via SIPN_CONFIG ── */
      var cfg = window.SIPN_CONFIG || {};
      var isAuthed = cfg.userIsAuthenticated || false;
      if (!isAuthed) {
        window.location.href = (cfg.urls && cfg.urls.login ? cfg.urls.login : '/accounts/login/') + '?next=' + encodeURIComponent(window.location.pathname + window.location.search);
        return;
      }
      var csrf = (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';
      var devisUrl = cfg.urls && cfg.urls.ambulanceTrajetDevis ? cfg.urls.ambulanceTrajetDevis : '/cart/ambulance-trajet-devis/';
      fetch(devisUrl, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({ org_id: st.structId, acte_name: st.acte, lines: lines, total_patient: r.surDevis ? 0 : (r.total || 0), sur_devis: !!r.surDevis, config_summary: configParts.join(' · ') })
      })
        .then(function (resp) { return resp.json().then(function (data) { return { ok: resp.ok, data: data }; }); })
        .then(function (result) {
          if (!result.ok || !result.data || !result.data.ok) { trajetToast((result.data && result.data.error) || 'Impossible d\'envoyer la demande de devis.', 'error'); return; }
          if (window.closeProfilStruct) window.closeProfilStruct();
          window.location.href = result.data.redirect;
        })
        .catch(function () { trajetToast('Erreur réseau. Réessayez.', 'error'); });
    }

    function openTrajetConfig(orgId, acteName, isCompPanel) {
      curActe = acteName;
      window.curActe = acteName;
      if (window.openProfilStruct) {
        window.openProfilStruct(orgId);
      } else {
        initTrajetConfig(orgId);
        if (acteName) focusTrajetActe(acteName, orgId);
        var containerId = isCompPanel ? 'trajet-config-comp-' + acteName : 'trajet-config-' + orgId;
        var container = document.getElementById(containerId);
        if (container) { container.classList.remove('hidden'); container.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      }
    }

    function closeTrajetConfig(orgId) {
      var container = document.getElementById('trajet-config-' + orgId);
      if (container) container.classList.add('hidden');
      TRAJET_STATE = null; curActe = null; window.curActe = null;
    }

    function focusTrajetActe(acte, structId) {
      var sid = structId || (TRAJET_STATE ? TRAJET_STATE.structId : null);
      if (!TRAJET_STATE && sid) initTrajetConfig(sid);
      if (!TRAJET_STATE) return;
      var resolvedActe = acte;
      if (TRAJET_DATA[String(TRAJET_STATE.structId)] && TRAJET_DATA[String(TRAJET_STATE.structId)].actes) {
        if (!TRAJET_DATA[String(TRAJET_STATE.structId)].actes[acte]) {
          resolvedActe = resolveTrajetActe(TRAJET_STATE.structId, acte) || Object.keys(TRAJET_DATA[String(TRAJET_STATE.structId)].actes)[0];
        }
      }
      TRAJET_STATE.acte = resolvedActe;
      renderTrajetConfig();
      var el = document.getElementById('trajet-config-content-' + TRAJET_STATE.structId) ||
        document.getElementById('trajet-config-' + TRAJET_STATE.structId) ||
        document.getElementById('trajet-config-comp-' + acte);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function toggleContactProfil() {
      var card = document.getElementById('profil-contact-card');
      if (card) card.style.display = (card.style.display === 'none' ? 'block' : 'none');
    }

    /* Expose globally */
    window.TRAJET_DATA = TRAJET_DATA;
    window.TRAJET_STATE = TRAJET_STATE;
    window.curActe = curActe;
    window.openTrajetConfig = openTrajetConfig;
    window.closeTrajetConfig = closeTrajetConfig;
    window.renderTrajetConfig = renderTrajetConfig;
    window.updateTrajetRecap = updateTrajetRecap;
    window.focusTrajetActe = focusTrajetActe;
    window.toggleContactProfil = toggleContactProfil;
    window.addEtape = addEtape;
    window.removeEtape = removeEtape;
    window.useMyLocation = useMyLocation;
    window.obtenirDevisTrajet = obtenirDevisTrajet;
    window.initTrajetConfig = initTrajetConfig;
    window.resolveTrajetActe = resolveTrajetActe;

    reinitActeMultiSelect();
    initAmbulanceTrajetConfig();
    if (typeof checkAndToggleResults === 'function') checkAndToggleResults();
  })();

}());

