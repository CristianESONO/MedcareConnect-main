/**
 * Fiche organisme publique : filtres, panier sélection, devis messagerie MedCare, contact vCard.
 */
(function () {
  var root = document.querySelector('[data-org-fiche]');
  if (!root) return;

  var profilPanier = [];
  var toastEl = document.getElementById('org-fiche-toast');

  function toast(msg, kind) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.remove('hidden', 'text-emerald-700', 'text-amber-700');
    toastEl.classList.add(kind === 'warn' ? 'text-amber-700' : 'text-emerald-700');
    setTimeout(function () { toastEl.classList.add('hidden'); }, 3500);
  }

  function getFicheScrollOffset() {
    var topBar = document.querySelector('.org-fiche-mobile-top');
    var nav = document.getElementById('org-fiche-mobile-nav');
    var offset = 12;
    if (topBar) offset += topBar.offsetHeight;
    if (nav) offset += nav.offsetHeight;
    return offset;
  }

  function scrollToActesAccordion(opts) {
    opts = opts || {};
    var target = document.getElementById('org-section-actes') || document.getElementById('pp-actes-list');
    if (!target) return;

    document.querySelectorAll('.pp-cat-group').forEach(function (el) {
      el.open = true;
    });

    var y = target.getBoundingClientRect().top + window.pageYOffset - getFicheScrollOffset();
    window.scrollTo({ top: Math.max(0, y), behavior: opts.instant ? 'auto' : 'smooth' });

    var list = document.getElementById('pp-actes-list');
    if (list) {
      list.classList.remove('pp-actes-list--highlight');
      window.requestAnimationFrame(function () {
        list.classList.add('pp-actes-list--highlight');
        window.setTimeout(function () {
          list.classList.remove('pp-actes-list--highlight');
        }, 1200);
      });
    }

    var nav = document.getElementById('org-fiche-mobile-nav');
    if (nav) {
      nav.querySelectorAll('[data-org-section]').forEach(function (link) {
        link.classList.toggle('is-active', link.getAttribute('data-org-section') === 'actes');
      });
    }
  }

  document.querySelectorAll('.js-scroll-to-actes').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      scrollToActesAccordion();
    });
  });

  if (window.location.hash === '#actes' || window.location.hash === '#org-section-actes') {
    window.setTimeout(function () { scrollToActesAccordion(); }, 350);
  }

  var btnHours = document.getElementById('btn-pp-hours');
  var cardHours = document.getElementById('pp-hours-card');
  if (btnHours && cardHours) {
    btnHours.addEventListener('click', function () {
      var hidden = cardHours.classList.toggle('hidden');
      btnHours.setAttribute('aria-expanded', hidden ? 'false' : 'true');
    });
  }

  function updateInsEmpty(filterVal) {
    var emptyEl = document.getElementById('pp-ins-empty');
    var listEl = document.getElementById('pp-ins-list');
    if (!emptyEl || !listEl) return;
    var visible = 0;
    listEl.querySelectorAll('.pp-ins-tag').forEach(function (tag) {
      if (tag.style.display !== 'none') visible += 1;
    });
    if (filterVal === 'all' || visible > 0) {
      emptyEl.classList.add('hidden');
      listEl.classList.remove('hidden');
    } else {
      emptyEl.classList.remove('hidden');
      listEl.classList.add('hidden');
    }
  }

  document.querySelectorAll('.pp-ins-filter').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.pp-ins-filter').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var val = btn.getAttribute('data-filter') || 'all';
      document.querySelectorAll('.pp-ins-tag').forEach(function (el) {
        var v = el.getAttribute('data-filter') || '';
        el.style.display = (val === 'all' || v === val) ? '' : 'none';
      });
      updateInsEmpty(val);
    });
  });

  document.querySelectorAll('.pp-cat-filter').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.pp-cat-filter').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var val = btn.getAttribute('data-cat') || 'all';
      document.querySelectorAll('.pp-cat-group').forEach(function (el) {
        var v = el.getAttribute('data-cat') || '';
        el.style.display = (val === 'all' || v === val) ? '' : 'none';
      });
    });
  });


  function syncCheckboxes() {
    document.querySelectorAll('.pp-acte-cb').forEach(function (cb) {
      var id = cb.getAttribute('data-id');
      cb.checked = profilPanier.some(function (p) { return p.id === id; });
    });
  }

  function updatePanier() {
    var count = profilPanier.length;
    var total = profilPanier.reduce(function (s, p) { return s + p.prix; }, 0);
    var countEl = document.getElementById('panier-count');
    var recapEl = document.getElementById('panier-recap');
    var itemsEl = document.getElementById('panier-items');
    var totalEl = document.getElementById('panier-total');
    var label = count + ' acte' + (count > 1 ? 's' : '') + ' sélectionné' + (count > 1 ? 's' : '');
    if (countEl) countEl.textContent = label;
    if (recapEl) recapEl.classList.toggle('hidden', count === 0);
    if (itemsEl) {
      itemsEl.innerHTML = profilPanier.map(function (p) {
        return '<span class="pp-panier-tag">' + p.nom
          + '<button type="button" class="pp-panier-remove" data-remove="' + p.id + '" aria-label="Retirer">&times;</button></span>';
      }).join('');
      itemsEl.querySelectorAll('[data-remove]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var rid = btn.getAttribute('data-remove');
          profilPanier = profilPanier.filter(function (x) { return x.id !== rid; });
          updatePanier();
          syncCheckboxes();
        });
      });
    }
    if (totalEl) totalEl.textContent = total.toLocaleString('fr-FR') + ' FCFA estimé';
    var stickyCount = document.getElementById('org-sticky-count');
    var stickyTotal = document.getElementById('org-sticky-total');
    if (stickyCount) {
      if (count === 0) {
        stickyCount.classList.add('hidden');
        stickyCount.textContent = '';
      } else {
        stickyCount.classList.remove('hidden');
        stickyCount.textContent = label;
      }
    }
    if (stickyTotal) {
      if (count > 0) {
        stickyTotal.textContent = total.toLocaleString('fr-FR') + ' FCFA';
        stickyTotal.classList.remove('hidden');
      } else {
        stickyTotal.textContent = '';
        stickyTotal.classList.add('hidden');
      }
    }
  }

  document.querySelectorAll('.pp-acte-cb').forEach(function (cb) {
    cb.addEventListener('change', function () {
      var id = cb.getAttribute('data-id');
      var nom = cb.getAttribute('data-nom') || '';
      var prix = parseInt(cb.getAttribute('data-prix') || '0', 10) || 0;
      if (cb.checked) {
        if (!profilPanier.some(function (p) { return p.id === id; })) {
          profilPanier.push({ id: id, nom: nom, prix: prix });
        }
      } else {
        profilPanier = profilPanier.filter(function (p) { return p.id !== id; });
      }
      updatePanier();
    });
  });

  var btnVider = document.getElementById('btn-vider-panier');
  if (btnVider) {
    btnVider.addEventListener('click', function () {
      profilPanier = [];
      updatePanier();
      syncCheckboxes();
    });
  }

  function getCsrfToken() {
    var el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
  }

  function requestPlatformDevis() {
    if (profilPanier.length === 0) {
      toast('Sélectionnez au moins un acte pour obtenir un devis.', 'warn');
      return;
    }
    var isPatient = root.getAttribute('data-is-patient') === 'true';
    if (!isPatient) {
      var loginUrl = root.getAttribute('data-login-url') || '';
      toast('Connectez-vous pour demander un devis.', 'warn');
      if (loginUrl) {
        window.setTimeout(function () { window.location.href = loginUrl; }, 700);
      }
      return;
    }
    var action = root.getAttribute('data-request-devis-url') || '';
    var orgSlug = root.getAttribute('data-org-slug') || '';
    if (!action || !orgSlug) return;

    var formData = new FormData();
    formData.append('org_slug', orgSlug);
    profilPanier.forEach(function (p) {
      formData.append('actes', p.id);
    });

    document.querySelectorAll('.js-devis-cta').forEach(function (btn) {
      btn.disabled = true;
    });

    fetch(action, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'application/json',
      },
      body: formData,
      credentials: 'same-origin',
    })
      .then(function (resp) {
        return resp.json().then(function (data) {
          if (!resp.ok || !data.ok) {
            throw new Error((data && data.error) || 'Impossible de préparer votre devis.');
          }
          if (data.redirect) {
            window.location.href = data.redirect;
            return;
          }
          throw new Error('Réponse inattendue du serveur.');
        });
      })
      .catch(function (err) {
        document.querySelectorAll('.js-devis-cta').forEach(function (btn) {
          btn.disabled = false;
        });
        toast(err.message || 'Une erreur est survenue.', 'warn');
      });
  }

  document.querySelectorAll('.js-devis-cta').forEach(function (btn) {
    btn.addEventListener('click', requestPlatformDevis);
  });

  (function initMobileSectionNav() {
    var nav = document.getElementById('org-fiche-mobile-nav');
    if (!nav) return;
    var links = Array.prototype.slice.call(nav.querySelectorAll('[data-org-section]'));
    var sections = {
      actes: document.getElementById('org-section-actes'),
      infos: document.getElementById('org-section-infos'),
    };

    function scrollOffset() {
      return getFicheScrollOffset();
    }

    function setActive(key) {
      links.forEach(function (link) {
        link.classList.toggle('is-active', link.getAttribute('data-org-section') === key);
      });
    }

    links.forEach(function (link) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        var key = link.getAttribute('data-org-section');
        var target = sections[key];
        if (!target) return;
        var y = target.getBoundingClientRect().top + window.pageYOffset - scrollOffset();
        window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
        setActive(key);
      });
    });

    if (!window.IntersectionObserver) return;
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var id = entry.target.id;
        if (id === 'org-section-actes') setActive('actes');
        if (id === 'org-section-infos') setActive('infos');
      });
    }, { root: null, rootMargin: '-' + scrollOffset() + 'px 0px -55% 0px', threshold: 0.05 });
    Object.keys(sections).forEach(function (k) {
      if (sections[k]) observer.observe(sections[k]);
    });
  })();

  updatePanier();
})();
