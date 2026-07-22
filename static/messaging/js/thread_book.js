/** Prise / modification de RDV embarquée dans un fil messagerie (POST puis redirect). */
(function () {
  'use strict';

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function gtime() {
    var n = new Date();
    return ('0' + n.getHours()).slice(-2) + ':' + ('0' + n.getMinutes()).slice(-2);
  }

  function chatScroll(chat) {
    if (!chat) return;
    chat.scrollTop = chat.scrollHeight;
  }

  function chatAppend(flowRoot, html) {
    var tmp = document.createElement('div');
    tmp.innerHTML = html;
    while (tmp.firstChild) {
      flowRoot.appendChild(tmp.firstChild);
    }
    var chat = flowRoot.id === 'mc-thread-chat' ? flowRoot : flowRoot.closest('#mc-thread-chat');
    chatScroll(chat || flowRoot);
  }

  function formatPrice(n) {
    var v = parseInt(n, 10);
    if (isNaN(v)) return String(n || '0');
    return v.toLocaleString('fr-FR');
  }

  function initRoot(root) {
    if (!root || root.getAttribute('data-mc-book-init')) return;
    root.setAttribute('data-mc-book-init', '1');

    var chat = qs('#mc-thread-chat', root) || qs('#pac-chat', root);
    var flowRoot = qs('#mc-book-insert', root) || chat;
    var dataEl = qs('#pac-book-data', root);
    if (!chat || !dataEl || !flowRoot) return;

    var orgName = root.getAttribute('data-org-name') || dataEl.getAttribute('data-org') || 'La structure';
    var data, bookUrl = root.getAttribute('data-book-url'), csrf = root.getAttribute('data-csrf');
    var successUrl = root.getAttribute('data-success-url') || '';
    var intro = root.getAttribute('data-intro') || 'Je souhaite prendre rendez-vous.';
    var embed = root.getAttribute('data-embed') === '1';
    var isReschedule = bookUrl.indexOf('reschedule') !== -1;
    var hasDevisRequest = !!qs('#mc-devis-request-msg', root);

    function msgAssist(inner, extraClass) {
      return '<div class="mc-wmsg mc-wmsg--r mc-book-flow' + (extraClass ? ' ' + extraClass : '') + '">'
        + '<div class="mc-wmsg-sender mc-wmsg-sender--org">' + orgName + '</div>'
        + inner + '<div class="mc-wtime">' + gtime() + '</div></div>';
    }
    function msgS(inner) {
      return '<div class="mc-wmsg mc-wmsg--s mc-book-flow">' + inner + '<div class="mc-wtime">' + gtime() + '</div></div>';
    }

    try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
    if (data.org && !root.getAttribute('data-org-name')) orgName = data.org;

    var noteInput = qs('#pac-note-input', root);
    var sendBtn = qs('#pac-wsend', root);
    var state = { slot: null, slotLabel: '', asap: false, submitting: false };

    function disableInput() {
      noteInput.disabled = true;
      sendBtn.disabled = true;
      noteInput.value = '';
      noteInput.placeholder = "Sélectionnez d'abord un créneau…";
      sendBtn.setAttribute('aria-label', 'Confirmer');
    }

    function enableRecapInput() {
      noteInput.disabled = false;
      sendBtn.disabled = false;
      noteInput.placeholder = 'Message au secrétariat (facultatif)…';
      sendBtn.setAttribute('aria-label', 'Valider la demande');
    }

    function clearRecapStep() {
      qsa('.mc-book-recap-step', flowRoot).forEach(function (el) { el.remove(); });
    }

    function buildRecapCard(label) {
      var actesHtml = (data.actes || []).map(function (a) {
        var qty = a.quantity > 1 ? ' ×' + a.quantity : '';
        return '<div class="mc-book-recap-row">'
          + '<span class="mc-book-recap-acte">' + a.acte + qty + '</span>'
          + '<span class="mc-book-recap-price">' + formatPrice(a.price) + ' F</span>'
          + '</div>';
      }).join('');
      var actesCount = (data.actes || []).length;
      var title = isReschedule ? 'Récapitulatif — modification' : 'Récapitulatif de réservation';
      var validateLabel = isReschedule ? 'Valider le nouveau créneau' : 'Valider ma demande de RDV';

      return '<div class="mc-book-recap">'
        + '<div class="mc-book-recap-head">' + title + '</div>'
        + '<div class="mc-book-recap-body">'
        + '<div class="mc-book-recap-line"><span>Structure</span><strong>' + orgName + '</strong></div>'
        + (data.org_city ? '<div class="mc-book-recap-line"><span>Lieu</span><strong>' + data.org_city + '</strong></div>' : '')
        + '<div class="mc-book-recap-line mc-book-recap-line--slot"><span>Date &amp; heure</span><strong>' + label + '</strong></div>'
        + (data.part ? '<div class="mc-book-recap-line"><span>Devis</span><strong>Réf. ' + data.part + '</strong></div>' : '')
        + (actesHtml ? '<div class="mc-book-recap-sep"></div>'
          + '<div class="mc-book-recap-actes-lbl">' + actesCount + ' acte' + (actesCount > 1 ? 's' : '') + '</div>'
          + actesHtml
          + '<div class="mc-book-recap-total"><span>Total estimé</span><strong>' + formatPrice(data.total) + ' FCFA</strong></div>'
          : '')
        + '</div>'
        + '<div class="mc-book-recap-note">Vérifiez les informations ci-dessus, ajoutez un message si besoin, puis validez.</div>'
        + '<div class="mc-book-recap-actions">'
        + '<button type="button" class="mc-book-recap-btn mc-book-recap-btn--ok" data-confirm="1">' + validateLabel + '</button>'
        + '<button type="button" class="mc-book-recap-btn mc-book-recap-btn--muted" data-change="1">Modifier le créneau</button>'
        + '</div></div>';
    }

    function renderDays() {
      state.slot = null;
      state.slotLabel = '';
      state.asap = false;
      disableInput();
      qsa('.mc-book-flow', flowRoot).forEach(function (el) { el.remove(); });
      var chips = data.days.map(function (d, i) {
        return '<button type="button" class="pac-wchip pac-wchip--day" data-day="' + i + '"><span>' + d.short + '</span></button>';
      }).join('');
      var soonest = data.soonest
        ? '<button type="button" class="pac-wchip pac-wchip--soon" data-asap="1">Au plus vite</button>'
        : '';
      chatAppend(flowRoot, msgAssist(
        'Quel <strong>jour</strong> vous convient ?'
        + '<div class="pac-wchips pac-wchips--days">' + soonest + chips + '</div>'
      ));
    }

    function renderTimes(dayIndex) {
      clearRecapStep();
      var d = data.days[dayIndex];
      if (!hasDevisRequest) {
        chatAppend(flowRoot, msgS(intro));
      }
      var chips = d.slots.map(function (s) {
        if (!s.available) return '<span class="mc-wslot off">' + s.label + '</span>';
        return '<button type="button" class="mc-wslot" data-slot="' + s.value + '" data-slotlabel="' + d.label + ' · ' + s.label + '">' + s.label + '</button>';
      }).join('');
      setTimeout(function () {
        chatAppend(flowRoot, msgAssist(
          'Créneaux disponibles — <strong>' + d.label + '</strong>'
          + '<div class="mc-wcal"><div class="mc-wcal-head">Choisissez votre horaire</div>'
          + '<div class="mc-wcal-slots">' + chips + '</div></div>'
        ));
      }, 280);
    }

    function renderRecap(slot, label) {
      state.slot = slot;
      state.slotLabel = label;
      state.asap = slot === 'asap';
      clearRecapStep();
      chatAppend(flowRoot, msgS('📅 Créneau choisi : <strong>' + label + '</strong>'));
      setTimeout(function () {
        chatAppend(flowRoot, msgAssist(buildRecapCard(label), 'mc-book-recap-step'));
        enableRecapInput();
      }, 320);
    }

    function lockGroup(btn) {
      var group = btn.closest('.pac-wchips') || btn.closest('.mc-wcal-slots');
      if (!group) return;
      qsa('.pac-wchip, .mc-wslot', group).forEach(function (c) {
        if (c !== btn) {
          c.classList.add('pac-wchip--dim');
          c.style.pointerEvents = 'none';
        }
      });
      btn.classList.add('pac-wchip--sel');
    }

    function setSubmitting(active) {
      state.submitting = active;
      sendBtn.disabled = active;
      noteInput.disabled = active;
      qsa('[data-confirm]', flowRoot).forEach(function (btn) {
        btn.disabled = active;
        if (active) btn.textContent = 'Envoi en cours…';
      });
    }

    function submit() {
      if (!state.slot || state.submitting) return;
      setSubmitting(true);
      var fd = new FormData();
      fd.append('csrfmiddlewaretoken', csrf);
      fd.append('slot', state.slot);
      fd.append('note', noteInput.value || '');
      fetch(bookUrl, { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok && !r.redirected) throw new Error('HTTP ' + r.status);
          if (successUrl) { window.location.href = successUrl; return; }
          window.location.reload();
        })
        .catch(function () {
          setSubmitting(false);
          enableRecapInput();
          qsa('[data-confirm]', flowRoot).forEach(function (btn) {
            btn.textContent = isReschedule ? 'Valider le nouveau créneau' : 'Valider ma demande de RDV';
          });
          alert('Erreur lors de la réservation. Réessayez.');
        });
    }

    flowRoot.addEventListener('click', function (e) {
      var dayBtn = e.target.closest('[data-day]');
      if (dayBtn) { lockGroup(dayBtn); renderTimes(parseInt(dayBtn.getAttribute('data-day'), 10)); return; }
      var asapBtn = e.target.closest('[data-asap]');
      if (asapBtn) {
        lockGroup(asapBtn);
        renderRecap('asap', 'Au plus vite, selon les disponibilités de la structure');
        return;
      }
      var slotBtn = e.target.closest('[data-slot]');
      if (slotBtn) {
        lockGroup(slotBtn);
        renderRecap(slotBtn.getAttribute('data-slot'), slotBtn.getAttribute('data-slotlabel'));
        return;
      }
      if (e.target.closest('[data-confirm]')) { submit(); return; }
      if (e.target.closest('[data-change]')) { renderDays(); return; }
    });
    sendBtn.addEventListener('click', function () {
      if (!sendBtn.disabled && state.slot) submit();
    });
    noteInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && state.slot && !sendBtn.disabled) { e.preventDefault(); submit(); }
    });

    if (embed) {
      if (hasDevisRequest) {
        chatAppend(flowRoot, msgS('📅 Je souhaite prendre rendez-vous'));
      }
      setTimeout(renderDays, hasDevisRequest ? 350 : 200);
    } else {
      chatAppend(flowRoot, msgS(intro));
      setTimeout(renderDays, 250);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    qsa('[data-mc-thread-book]').forEach(initRoot);
  });
})();
