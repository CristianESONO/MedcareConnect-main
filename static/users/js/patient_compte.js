/**
 * Mon compte patient — layout sidebar + contenu (plein écran ou overlay depuis recherche).
 */
(function (window) {
  'use strict';

  var cfg = window.MEDCARE_PAC || {};
  var root = null;
  var content = null;
  var currentTab = 'accueil';
  var open = false;

  function qs(sel, ctx) {
    return (ctx || document).querySelector(sel);
  }
  function qsa(sel, ctx) {
    return Array.prototype.slice.call((ctx || document).querySelectorAll(sel));
  }

  function panelUrl(tab, devisRef) {
    if (devisRef) {
      return cfg.devisDetailUrl.replace('__REF__', encodeURIComponent(devisRef));
    }
    var map = cfg.tabUrls || {};
    return map[tab] || map.accueil || map.rdv;
  }

  function setTabActive(tab) {
    qsa('.js-pac-nav').forEach(function (link) {
      link.classList.toggle('active', link.getAttribute('data-pac-tab') === tab);
    });
  }

  function setPageTitle(tab) {
    var titles = cfg.pageTitles || {};
    var title = titles[tab] || 'Mon compte';
    qsa('#pac-content-title').forEach(function (el) {
      el.textContent = title;
    });
  }

  function setPageMode(tab) {
    qsa('#pac-page').forEach(function (page) {
      Array.prototype.slice.call(page.classList).forEach(function (cls) {
        if (cls.indexOf('pac-page--') === 0 && cls !== 'pac-page--overlay') {
          page.classList.remove(cls);
        }
      });
      page.classList.add('pac-page--' + (tab || 'accueil'));
    });
  }

  function initInsuranceForm(ctx) {
    var form = qs('#pac-ins-form', ctx);
    if (!form) return;
    var hidden = qs('#pac-has-insurance', form);
    var selZone = qs('#pac-ins-selector', form);
    var directZone = qs('#pac-ins-direct', form);
    var insSelect = qs('#id_insurance', form);
    qsa('[data-ins-yes]', form).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var yes = btn.getAttribute('data-ins-yes') === '1';
        if (hidden) hidden.value = yes ? '1' : '0';
        qsa('.pac-ins-yn-btn', form).forEach(function (b) {
          b.classList.remove('pac-ins-yn-btn--active');
        });
        btn.classList.add('pac-ins-yn-btn--active');
        if (selZone) selZone.classList.toggle('hidden', !yes);
        if (directZone) directZone.classList.toggle('hidden', yes);
        if (!yes && insSelect) insSelect.value = '';
      });
    });
    form.addEventListener('submit', function () {
      if (hidden && hidden.value === '0' && insSelect) insSelect.value = '';
    });
  }

  function gtime() {
    var n = new Date();
    return ('0' + n.getHours()).slice(-2) + ':' + ('0' + n.getMinutes()).slice(-2);
  }

  function chatAppend(chat, html) {
    var tmp = document.createElement('div');
    tmp.innerHTML = html;
    while (tmp.firstChild) chat.appendChild(tmp.firstChild);
    chat.scrollTop = chat.scrollHeight;
  }

  function msgR(inner) {
    return '<div class="pac-wmsg pac-wmsg--r">' + inner + '<div class="pac-wtime">' + gtime() + '</div></div>';
  }
  function msgS(inner) {
    return '<div class="pac-wmsg pac-wmsg--s">' + inner + '<div class="pac-wtime">' + gtime() + '</div></div>';
  }
  function msgSys(inner) {
    return '<div class="pac-wmsg pac-wmsg--sys">' + inner + '</div>';
  }

  function lockGroup(btn) {
    var group = btn.closest('.pac-wchips');
    if (!group) return;
    qsa('.pac-wchip', group).forEach(function (c) {
      if (c !== btn) c.classList.add('pac-wchip--dim');
      c.style.pointerEvents = 'none';
    });
    btn.classList.add('pac-wchip--sel');
  }

  function initBookChat(ctx) {
    var bookRoot = qs('#pac-book-root', ctx);
    if (!bookRoot) return;
    var chat = qs('#pac-chat', bookRoot);
    if (!chat) return;
    var dataEl = qs('#pac-book-data', bookRoot);
    if (!dataEl) return;
    var data;
    try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
    var bookUrl = bookRoot.getAttribute('data-book-url');
    var csrf = bookRoot.getAttribute('data-csrf');
    var noteInput = qs('#pac-note-input', bookRoot);
    var sendBtn = qs('#pac-wsend', bookRoot);
    if (!noteInput || !sendBtn) return;
    var state = { slot: null };

    function disableInput() {
      noteInput.disabled = true;
      sendBtn.disabled = true;
      noteInput.value = '';
      noteInput.placeholder = "Sélectionnez d'abord un créneau…";
    }
    function enableInput() {
      noteInput.disabled = false;
      sendBtn.disabled = false;
      noteInput.placeholder = 'Message au secrétariat (facultatif)…';
      setTimeout(function () { try { noteInput.focus(); } catch (e) {} }, 120);
    }

    function renderDays() {
      state.slot = null;
      disableInput();
      var chips = data.days.map(function (d, i) {
        return '<button type="button" class="pac-wchip" data-day="' + i + '">' + d.short + '</button>';
      }).join('');
      chatAppend(chat, msgR('Bonjour 👋 Pour <strong>' + data.org + '</strong>, choisissez le <strong>jour</strong> :'
        + '<div class="pac-wchips">' + chips + '</div>'));
    }

    function renderTimes(dayIndex) {
      var d = data.days[dayIndex];
      chatAppend(chat, msgS('📅 ' + d.label));
      var chips = d.slots.map(function (s) {
        if (!s.available) return '<span class="pac-wchip pac-wchip--off">' + s.label + '</span>';
        return '<button type="button" class="pac-wchip" data-slot="' + s.value + '" data-slotlabel="' + d.label + ' · ' + s.label + '">' + s.label + '</button>';
      }).join('');
      setTimeout(function () {
        chatAppend(chat, msgR('Voici les créneaux du <strong>' + d.label + '</strong> :'
          + '<div class="pac-wchips pac-wchips--times">' + chips + '</div>'));
      }, 350);
    }

    function renderConfirm(slot, label) {
      state.slot = slot;
      chatAppend(chat, msgS('🕐 ' + label));
      setTimeout(function () {
        chatAppend(chat, msgR(
          '<div class="pac-wa-fee">⏳ <strong>Réservation gratuite</strong> pendant la période Pionniers — les frais de 500 FCFA seront activés plus tard.</div>'
          + 'Ajoutez un message ci-dessous si besoin (facultatif), puis confirmez.'
          + '<div class="pac-wchips"><button type="button" class="pac-wchip pac-wchip--confirm" data-confirm="1">✅ Confirmer mon RDV</button>'
          + '<button type="button" class="pac-wchip" data-change="1">↩︎ Changer</button></div>'));
        enableInput();
      }, 400);
    }

    function submit() {
      if (!state.slot) return;
      var fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      fd.append('slot', state.slot);
      fd.append('note', noteInput.value || '');
      fetchPanel(bookUrl, 'POST', fd).then(injectHtml).catch(showError);
    }

    chat.addEventListener('click', function (e) {
      var dayBtn = e.target.closest('[data-day]');
      if (dayBtn) { lockGroup(dayBtn); renderTimes(parseInt(dayBtn.getAttribute('data-day'), 10)); return; }
      var slotBtn = e.target.closest('[data-slot]');
      if (slotBtn) { lockGroup(slotBtn); renderConfirm(slotBtn.getAttribute('data-slot'), slotBtn.getAttribute('data-slotlabel')); return; }
      var confirmBtn = e.target.closest('[data-confirm]');
      if (confirmBtn) { lockGroup(confirmBtn); submit(); return; }
      var changeBtn = e.target.closest('[data-change]');
      if (changeBtn) { lockGroup(changeBtn); renderDays(); return; }
    });
    sendBtn.addEventListener('click', function () { if (!sendBtn.disabled) submit(); });
    noteInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !sendBtn.disabled) { e.preventDefault(); submit(); }
    });

    chatAppend(chat, msgSys('Prise de rendez-vous · ' + gtime()));
    chatAppend(chat, msgS('Je souhaite prendre rendez-vous.'));
    setTimeout(renderDays, 300);
  }

  function getContentInner() {
    if (open && content) {
      return content.querySelector('.pac-inner') || content;
    }
    var pageInner = qs('#pac-page #pac-content .pac-inner');
    if (pageInner) return pageInner;
    if (content) return content.querySelector('.pac-inner') || content;
    return null;
  }

  function getContentScrollEl() {
    if (open && content) return content;
    return qs('#pac-page #pac-content') || content;
  }

  function bindPanelEvents(ctx) {
    qsa('.js-pac-tab', ctx).forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        if (open) {
          loadTab(btn.getAttribute('data-pac-tab'));
        } else {
          var tab = btn.getAttribute('data-pac-tab');
          var url = panelUrl(tab);
          if (url) {
            /* Supprimer le paramètre pac_partial pour la navigation normale */
            var navUrl = url.replace('?pac_partial=1', '').replace('&pac_partial=1', '');
            window.location.href = navUrl;
          }
        }
      });
    });
    qsa('.js-pac-devis-detail', ctx).forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        loadDevisDetail(btn.getAttribute('data-devis-ref'));
      });
    });
    qsa('.js-pac-load', ctx).forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        loadUrl(btn.getAttribute('data-pac-url'));
      });
    });
    initInsuranceForm(ctx);
    initBookChat(ctx);
  }

  function bindSidebarNav() {
    qsa('.pac-sidebar .js-pac-nav').forEach(function (link) {
      link.addEventListener('click', function (e) {
        if (!open && !qs('#pac-page')) return;
        e.preventDefault();
        loadTab(link.getAttribute('data-pac-tab'));
      });
    });
  }

  function fetchPanel(url, method, body) {
    var inner = getContentInner();
    if (inner) {
      inner.innerHTML = '<p class="pac-empty">Chargement…</p>';
    }
    var opts = {
      method: method || 'GET',
      credentials: 'same-origin',
      headers: { 'X-MedCare-PAC': '1' },
    };
    if (body) opts.body = body;
    return fetch(url, opts).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    });
  }

  function injectHtml(html) {
    var inner = getContentInner();
    if (!inner) return;
    inner.innerHTML = html;
    var marker = inner.querySelector('[data-pac-active]');
    if (marker) {
      currentTab = marker.getAttribute('data-pac-active');
      setTabActive(currentTab);
      setPageTitle(currentTab);
      setPageMode(currentTab);
    }
    bindPanelEvents(inner);
    var scrollEl = getContentScrollEl();
    if (scrollEl) scrollEl.scrollTop = 0;
  }

  function loadTab(tab) {
    currentTab = tab;
    setTabActive(tab);
    setPageTitle(tab);
    setPageMode(tab);
    return fetchPanel(panelUrl(tab)).then(injectHtml).catch(showError);
  }

  function loadDevisDetail(ref) {
    setTabActive('devis');
    setPageTitle('devis');
    setPageMode('devis');
    return fetchPanel(panelUrl('devis', ref)).then(injectHtml).catch(showError);
  }

  function loadUrl(url) {
    if (!url) return;
    return fetchPanel(url).then(injectHtml).catch(showError);
  }

  function showError() {
    var inner = getContentInner();
    if (!inner) return;
    inner.innerHTML = '<p class="pac-empty">Impossible de charger le contenu. Réessayez.</p>';
  }

  function openDrawer(tab, devisRef) {
    if (!root || !content) return;
    root.classList.add('pac-root--open');
    root.setAttribute('aria-hidden', 'false');
    document.body.classList.add('pac-drawer-open');
    open = true;
    if (devisRef) {
      loadDevisDetail(devisRef);
    } else {
      loadTab(tab || 'accueil');
    }
  }

  function closeDrawer() {
    if (!root || !open) return;
    root.classList.remove('pac-root--open');
    root.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('pac-drawer-open');
    open = false;
    var url = new URL(window.location.href);
    if (url.searchParams.has('pac') || url.searchParams.has('devis_ref')) {
      url.searchParams.delete('pac');
      url.searchParams.delete('devis_ref');
      window.history.replaceState({}, '', url.pathname + url.search + url.hash);
    }
  }

  function onFormSubmit(e) {
    var form = e.target;
    if (!open || !content || !content.contains(form)) return;
    if ((form.method || '').toLowerCase() !== 'post') return;
    e.preventDefault();
    var fd = new FormData(form);
    fetchPanel(form.action, 'POST', fd).then(injectHtml).catch(showError);
  }

  function init() {
    root = qs('#pac-root');
    content = qs('#pac-overlay-content');
    var fullPage = qs('#pac-page');
    var pageContent = qs('#pac-page #pac-content');

    if (fullPage && pageContent) {
      bindPanelEvents(pageContent);
    }

    if (root && content) {
      qs('#pac-close-btn')?.addEventListener('click', closeDrawer);
      qs('#pac-backdrop')?.addEventListener('click', closeDrawer);
      bindSidebarNav();
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && open) closeDrawer();
      });
      document.addEventListener('submit', onFormSubmit, true);

      document.addEventListener('click', function (e) {
        var t = e.target.closest('.js-pac-open');
        if (!t) return;
        e.preventDefault();
        openDrawer(t.getAttribute('data-pac-tab') || 'accueil');
      });

      var params = new URLSearchParams(window.location.search);
      var pac = params.get('pac');
      if (pac) {
        openDrawer(pac, params.get('devis_ref'));
      }
    }
  }

  window.MedCarePatientAccount = {
    open: openDrawer,
    close: closeDrawer,
    loadTab: loadTab,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
