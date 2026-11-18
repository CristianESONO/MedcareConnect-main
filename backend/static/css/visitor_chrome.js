(function () {
  var burger = document.getElementById('mcLandingBurger');
  var drawer = document.getElementById('mcLandingDrawer');
  var backdrop = document.getElementById('mcLandingDrawerBackdrop');

  if (!burger || !drawer || !backdrop) return;

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
    if (window.innerWidth > 1024) setDrawerOpen(false);
  });
})();
