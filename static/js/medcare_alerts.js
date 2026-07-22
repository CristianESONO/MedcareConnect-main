/**
 * MedCare UI — toasts & confirmations modernes (remplace alert/confirm natifs).
 */
(function (global) {
  'use strict';

  var ICONS = {
    success: '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>',
    error: '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"/></svg>',
    warning: '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"/></svg>',
    info: '<svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"/></svg>',
  };

  var reduceMotion = false;
  var confirmRoot = null;
  var confirmResolve = null;

  function ensureStack() {
    var stack = document.getElementById('medcare-toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.id = 'medcare-toast-stack';
      stack.className = 'medcare-toast-stack';
      stack.setAttribute('aria-live', 'polite');
      stack.setAttribute('aria-relevant', 'additions');
      document.body.appendChild(stack);
    }
    return stack;
  }

  function ensureConfirmRoot() {
    if (confirmRoot) return confirmRoot;
    confirmRoot = document.createElement('div');
    confirmRoot.id = 'medcare-confirm-root';
    confirmRoot.className = 'medcare-confirm-root';
    confirmRoot.setAttribute('role', 'dialog');
    confirmRoot.setAttribute('aria-modal', 'true');
    confirmRoot.setAttribute('aria-hidden', 'true');
    confirmRoot.innerHTML =
      '<div class="medcare-confirm-dialog">' +
      '  <div class="medcare-confirm-icon" aria-hidden="true">' +
      '    <svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"/></svg>' +
      '  </div>' +
      '  <h2 class="medcare-confirm-title" id="medcare-confirm-title">Confirmation</h2>' +
      '  <p class="medcare-confirm-message" id="medcare-confirm-message"></p>' +
      '  <div class="medcare-confirm-actions">' +
      '    <button type="button" class="medcare-confirm-btn medcare-confirm-btn--ok" id="medcare-confirm-ok">Confirmer</button>' +
      '    <button type="button" class="medcare-confirm-btn medcare-confirm-btn--cancel" id="medcare-confirm-cancel">Annuler</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(confirmRoot);

    confirmRoot.addEventListener('click', function (e) {
      if (e.target === confirmRoot) closeConfirm(false);
    });
    document.getElementById('medcare-confirm-cancel').addEventListener('click', function () {
      closeConfirm(false);
    });
    document.getElementById('medcare-confirm-ok').addEventListener('click', function () {
      closeConfirm(true);
    });
    document.addEventListener('keydown', function (e) {
      if (!confirmRoot.classList.contains('is-open')) return;
      if (e.key === 'Escape') closeConfirm(false);
    });
    return confirmRoot;
  }

  function closeConfirm(result) {
    if (!confirmRoot || !confirmResolve) return;
    confirmRoot.classList.remove('is-open');
    confirmRoot.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    var resolve = confirmResolve;
    confirmResolve = null;
    resolve(!!result);
  }

  function removeToast(el) {
    if (!el || el.getAttribute('data-medcare-toast-removed')) return;
    el.setAttribute('data-medcare-toast-removed', '1');
    if (reduceMotion) {
      el.remove();
      return;
    }
    el.style.animation = 'medcareToastOut 0.22s ease forwards';
    setTimeout(function () { el.remove(); }, 220);
  }

  function toast(message, opts) {
    opts = opts || {};
    var level = opts.level || opts.type || 'info';
    if (level === 'danger') level = 'error';
    var duration = opts.duration;
    if (duration == null) {
      duration = (level === 'error' || level === 'warning') ? 8000 : 5600;
    }

    var stack = ensureStack();
    var el = document.createElement('div');
    el.setAttribute('role', 'alert');
    el.setAttribute('data-medcare-toast', '');
    el.setAttribute('data-toast-level', level);
    el.className = 'medcare-toast medcare-toast--' + level;
    el.innerHTML =
      '<span class="medcare-toast__icon" aria-hidden="true">' + (ICONS[level] || ICONS.info) + '</span>' +
      '<p class="medcare-toast__text"></p>' +
      '<button type="button" data-medcare-toast-close class="medcare-toast__close" aria-label="Fermer">' +
      '<svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>' +
      '</button>';
    el.querySelector('.medcare-toast__text').textContent = String(message || '');
    el.querySelector('[data-medcare-toast-close]').addEventListener('click', function () {
      removeToast(el);
    });
    stack.appendChild(el);
    if (duration > 0 && !reduceMotion) {
      setTimeout(function () { removeToast(el); }, duration);
    }
    return el;
  }

  function alertModal(message, opts) {
    opts = opts || {};
    return confirm(String(message || ''), {
      title: opts.title || 'Information',
      confirmLabel: opts.okLabel || 'OK',
      cancelLabel: null,
      danger: false,
    });
  }

  function confirm(message, opts) {
    opts = opts || {};
    ensureConfirmRoot();
    return new Promise(function (resolve) {
      if (confirmResolve) closeConfirm(false);
      confirmResolve = resolve;

      var titleEl = document.getElementById('medcare-confirm-title');
      var msgEl = document.getElementById('medcare-confirm-message');
      var okBtn = document.getElementById('medcare-confirm-ok');
      var cancelBtn = document.getElementById('medcare-confirm-cancel');

      titleEl.textContent = opts.title || 'Confirmer l\'action';
      msgEl.textContent = String(message || '');
      okBtn.textContent = opts.confirmLabel || opts.okLabel || 'Confirmer';
      cancelBtn.textContent = opts.cancelLabel || 'Annuler';

      okBtn.className = 'medcare-confirm-btn ' + (opts.danger ? 'medcare-confirm-btn--danger' : 'medcare-confirm-btn--ok');

      if (opts.cancelLabel === null || opts.hideCancel) {
        cancelBtn.style.display = 'none';
      } else {
        cancelBtn.style.display = '';
      }

      confirmRoot.classList.add('is-open');
      confirmRoot.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      setTimeout(function () { okBtn.focus(); }, 50);
    });
  }

  function extractConfirmMsg(attr) {
    if (!attr) return null;
    var m = attr.match(/confirm\s*\(\s*(['"])([\s\S]*?)\1\s*\)/);
    return m ? m[2] : null;
  }

  function upgradeLegacyConfirms() {
    document.querySelectorAll('form[onsubmit*="confirm("]').forEach(function (form) {
      var msg = extractConfirmMsg(form.getAttribute('onsubmit'));
      if (!msg) return;
      form.removeAttribute('onsubmit');
      form.setAttribute('data-medcare-confirm', msg);
      if (/supprimer|archiver|refuser|annuler|vider/i.test(msg)) {
        form.setAttribute('data-medcare-confirm-danger', '1');
      }
    });

    document.querySelectorAll('[onclick*="confirm("]').forEach(function (el) {
      var msg = extractConfirmMsg(el.getAttribute('onclick'));
      if (!msg) return;
      el.removeAttribute('onclick');
      el.setAttribute('data-medcare-confirm', msg);
      if (/supprimer|archiver|refuser|annuler|vider/i.test(msg)) {
        el.setAttribute('data-medcare-confirm-danger', '1');
      }
    });
  }

  function bindConfirmHandlers() {
    document.addEventListener('submit', function (e) {
      var form = e.target;
      if (!form || !form.getAttribute || !form.getAttribute('data-medcare-confirm')) return;
      if (form.dataset.medcareConfirmed === '1') {
        delete form.dataset.medcareConfirmed;
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      var msg = form.getAttribute('data-medcare-confirm');
      var danger = form.hasAttribute('data-medcare-confirm-danger');
      confirm(msg, { title: 'Confirmer', danger: danger }).then(function (ok) {
        if (!ok) return;
        form.dataset.medcareConfirmed = '1';
        if (typeof form.requestSubmit === 'function') form.requestSubmit();
        else form.submit();
      });
    }, true);

    document.addEventListener('click', function (e) {
      var el = e.target.closest('[data-medcare-confirm]');
      if (!el || el.tagName === 'FORM') return;
      if (el.dataset.medcareConfirmed === '1') {
        delete el.dataset.medcareConfirmed;
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      var msg = el.getAttribute('data-medcare-confirm');
      var danger = el.hasAttribute('data-medcare-confirm-danger');
      confirm(msg, { title: 'Confirmer', danger: danger }).then(function (ok) {
        if (!ok) return;
        if (el.tagName === 'A' && el.href) {
          window.location.href = el.href;
          return;
        }
        if (el.tagName === 'BUTTON') {
          var form = el.form;
          if (form) {
            if (el.name && el.value) {
              var hidden = document.createElement('input');
              hidden.type = 'hidden';
              hidden.name = el.name;
              hidden.value = el.value;
              form.appendChild(hidden);
            }
            form.dataset.medcareConfirmed = '1';
            if (typeof form.requestSubmit === 'function') form.requestSubmit(el);
            else form.submit();
            return;
          }
          el.dataset.medcareConfirmed = '1';
          el.click();
        }
      });
    }, true);
  }

  function initExistingToasts() {
    var stack = document.getElementById('medcare-toast-stack');
    if (!stack) return;
    stack.querySelectorAll('[data-medcare-toast]').forEach(function (el) {
      var level = el.getAttribute('data-toast-level') || 'info';
      var delay = (level === 'error' || level === 'warning') ? 0 : 5600;
      if (delay && !reduceMotion) setTimeout(function () { removeToast(el); }, delay);
      var btn = el.querySelector('[data-medcare-toast-close]');
      if (btn) btn.addEventListener('click', function () { removeToast(el); });
    });
  }

  function patchNativeDialogs() {
    global.alert = function (message) {
      toast(String(message), { level: 'info', duration: 6500 });
    };
    /* confirm() synchrone : les onclick/onsubmit legacy sont migrés via upgradeLegacyConfirms */
    global.confirm = function () {
      console.warn('[MedcareUI] window.confirm() synchrone non supporté — utilisez data-medcare-confirm ou MedcareUI.confirm()');
      return false;
    };
  }

  function init() {
    reduceMotion = global.matchMedia('(prefers-reduced-motion: reduce)').matches;
    ensureStack();
    upgradeLegacyConfirms();
    bindConfirmHandlers();
    initExistingToasts();
    patchNativeDialogs();
  }

  var MedcareUI = {
    toast: toast,
    alert: alertModal,
    confirm: confirm,
    init: init,
  };

  global.MedcareUI = MedcareUI;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(typeof window !== 'undefined' ? window : this);
