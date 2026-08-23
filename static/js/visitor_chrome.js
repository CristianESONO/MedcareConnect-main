(function () {
  var burger = document.getElementById('mcLandingBurger');
  var drawer = document.getElementById('mcLandingDrawer');
  var backdrop = document.getElementById('mcLandingDrawerBackdrop');

  if (burger && drawer && backdrop) {
    function setDrawerOpen(open) {
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      drawer.classList.toggle('is-open', open);
      drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
      backdrop.hidden = !open;
      backdrop.classList.toggle('is-visible', open);
      backdrop.setAttribute('aria-hidden', open ? 'false' : 'true');
      document.body.classList.toggle('mc-visitor-drawer-open', open);
    }

    burger.addEventListener('click', function () {
      setDrawerOpen(burger.getAttribute('aria-expanded') !== 'true');
    });
    backdrop.addEventListener('click', function () {
      setDrawerOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setDrawerOpen(false);
    });
    window.addEventListener('resize', function () {
      var isPatient = document.body.getAttribute('data-medcare-is-patient') === 'true';
      var minNavWidth = isPatient ? 1110 : 768;
      if (window.innerWidth >= minNavWidth) setDrawerOpen(false);
    });

    document.querySelectorAll('.js-visitor-drawer-close').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        setDrawerOpen(false);
        var dashDrawer = document.getElementById('dashAppDrawer');
        var dashBackdrop = document.getElementById('dashAppDrawerBackdrop');
        if (dashDrawer) dashDrawer.classList.remove('is-open');
        if (dashBackdrop) dashBackdrop.hidden = true;
      });
    });
  }

  window.openPrestataireDrawer = function (e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    var drawer = document.getElementById('dashAppDrawer') || document.getElementById('mcLandingDrawer');
    var backdrop = document.getElementById('dashAppDrawerBackdrop') || document.getElementById('mcLandingDrawerBackdrop');
    if (drawer && backdrop) {
      drawer.classList.add('is-open');
      drawer.setAttribute('aria-hidden', 'false');
      backdrop.hidden = false;
      backdrop.classList.add('is-visible');
      backdrop.setAttribute('aria-hidden', 'false');
      document.body.classList.add('mc-visitor-drawer-open');
    } else {
      window.location.href = '/healthcare/prestataire/dashboard/';
    }
  };

  var dashBackdrop = document.getElementById('dashAppDrawerBackdrop');
  if (dashBackdrop) {
    dashBackdrop.addEventListener('click', function () {
      var drawer = document.getElementById('dashAppDrawer');
      if (drawer) drawer.classList.remove('is-open');
      dashBackdrop.hidden = true;
      document.body.classList.remove('mc-visitor-drawer-open');
    });
  }

  document.addEventListener('click', function (e) {
    var patientClose = e.target.closest('.js-patient-drawer-close');
    if (!patientClose) return;
    e.preventDefault();
    if (typeof window._sipnCloseMenuView === 'function') {
      window._sipnCloseMenuView();
      return;
    }
    /* Header drawer ouvert : fermeture gérée par .js-visitor-drawer-close */
    var headerDrawer = document.getElementById('mcLandingDrawer');
    if (headerDrawer && headerDrawer.classList.contains('is-open')) return;
    var fallback = patientClose.getAttribute('data-fallback-href');
    if (fallback) window.location.href = fallback;
  });

  document.querySelectorAll('.mc-landing-nav-dropdown').forEach(function (dropdown) {
    var trigger = dropdown.querySelector('.mc-landing-nav-dropdown-trigger');
    if (!trigger) return;

    function setOpen(open) {
      dropdown.classList.toggle('is-open', open);
      trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      var willOpen = !dropdown.classList.contains('is-open');
      document.querySelectorAll('.mc-landing-nav-dropdown.is-open').forEach(function (other) {
        if (other !== dropdown) {
          other.classList.remove('is-open');
          var otherTrigger = other.querySelector('.mc-landing-nav-dropdown-trigger');
          if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
        }
      });
      setOpen(willOpen);
    });
  });

  document.addEventListener('click', function () {
    document.querySelectorAll('.mc-landing-nav-dropdown.is-open').forEach(function (dropdown) {
      dropdown.classList.remove('is-open');
      var trigger = dropdown.querySelector('.mc-landing-nav-dropdown-trigger');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    document.querySelectorAll('.mc-landing-nav-dropdown.is-open').forEach(function (dropdown) {
      dropdown.classList.remove('is-open');
      var trigger = dropdown.querySelector('.mc-landing-nav-dropdown-trigger');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  });
})();
