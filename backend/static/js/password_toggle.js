(function () {
  var EYE_SHOW = '<svg class="mc-password-toggle-icon mc-password-toggle-icon--show" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_HIDE = '<svg class="mc-password-toggle-icon mc-password-toggle-icon--hide" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>';

  function bindToggleButton(input, btn) {
    if (!input || !btn || btn.dataset.pwBound === '1') return;
    btn.dataset.pwBound = '1';

    btn.addEventListener('click', function () {
      var visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      btn.classList.toggle('is-visible', !visible);
      btn.setAttribute('aria-label', visible ? 'Afficher le mot de passe' : 'Masquer le mot de passe');
      btn.setAttribute('aria-pressed', visible ? 'false' : 'true');
    });
  }

  function wrapPasswordInput(input) {
    if (!input || input.type !== 'password' || input.dataset.pwToggle === '1') {
      return;
    }

    var existingWrap = input.closest('.mc-password-wrap');
    if (existingWrap) {
      var existingBtn = existingWrap.querySelector('.mc-password-toggle');
      if (existingBtn) {
        bindToggleButton(input, existingBtn);
      }
      input.dataset.pwToggle = '1';
      return;
    }

    input.dataset.pwToggle = '1';

    var wrap = document.createElement('div');
    wrap.className = 'mc-password-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'mc-password-toggle';
    btn.setAttribute('aria-label', 'Afficher le mot de passe');
    btn.setAttribute('aria-pressed', 'false');
    btn.innerHTML = EYE_SHOW + EYE_HIDE;
    bindToggleButton(input, btn);
    wrap.appendChild(btn);
  }

  function initPasswordToggles(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('input[type="password"]').forEach(wrapPasswordInput);
  }

  window.MedcareInitPasswordToggles = initPasswordToggles;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initPasswordToggles(document);
    });
  } else {
    initPasswordToggles(document);
  }

  if (typeof MutationObserver !== 'undefined' && document.body) {
    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType !== 1) return;
          if (node.matches && node.matches('input[type="password"]')) {
            wrapPasswordInput(node);
          }
          initPasswordToggles(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
})();
