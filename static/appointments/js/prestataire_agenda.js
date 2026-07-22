/**
 * Agenda prestataire — grille semaine, modales, drag & drop RDV (multi-RDV par créneau).
 */
(function () {
  'use strict';

  var cfg = window.MEDCARE_AGENDA || {};
  var data = {};
  try {
    var el = document.getElementById('ag-rdv-data');
    if (el) data = JSON.parse(el.textContent || '{}');
  } catch (e) {}

  var addModal = document.getElementById('ag-add');
  var detailModal = document.getElementById('ag-detail');
  var toastEl = document.getElementById('ag-toast');
  var dragRef = null;

  function open(m) {
    if (!m) return;
    m.classList.add('open');
    m.setAttribute('aria-hidden', 'false');
  }
  function close(m) {
    if (!m) return;
    m.classList.remove('open');
    m.setAttribute('aria-hidden', 'true');
  }

  function toast(msg, isError) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.toggle('error', !!isError);
    toastEl.classList.add('show');
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () {
      toastEl.classList.remove('show');
    }, 2800);
  }

  function csrf() {
    var inp = document.querySelector('input[name=csrfmiddlewaretoken]');
    return inp ? inp.value : '';
  }

  function openAddModal(slot, label) {
    var slotIn = document.getElementById('ag-add-slot');
    var whenEl = document.getElementById('ag-add-when');
    if (slotIn) slotIn.value = slot;
    if (whenEl) whenEl.textContent = label;
    open(addModal);
    var f = addModal && addModal.querySelector('input[name="name"]');
    if (f) setTimeout(function () { f.focus(); }, 50);
  }

  document.querySelectorAll('.ag-close').forEach(function (b) {
    b.addEventListener('click', function () {
      close(addModal);
      close(detailModal);
    });
  });
  [addModal, detailModal].forEach(function (m) {
    if (!m) return;
    m.addEventListener('click', function (e) {
      if (e.target === m) close(m);
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      close(addModal);
      close(detailModal);
    }
  });

  var STATUS_STYLE = {
    requested: ['bg-amber-100 text-amber-800', 'À confirmer'],
    confirmed: ['bg-emerald-50 text-emerald-700', 'Confirmé'],
    completed: ['bg-blue-50 text-blue-700', 'Honoré'],
    no_show: ['bg-rose-50 text-rose-700', 'Absent'],
    cancelled: ['bg-gray-200 text-gray-700', 'Annulé'],
    declined: ['bg-gray-200 text-gray-700', 'Refusé'],
  };

  function setRow(id, show, value) {
    var row = document.getElementById(id);
    if (!row) return;
    row.classList.toggle('hidden', !show);
    if (show && value !== undefined) row.textContent = value;
  }

  function showDetail(r) {
    document.getElementById('ag-d-name').textContent = r.name;
    document.getElementById('ag-d-when').textContent = r.when;

    var st = document.getElementById('ag-d-status');
    var style = STATUS_STYLE[r.status] || ['bg-gray-200 text-gray-700', r.status_label];
    st.className = 'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ' + style[0];
    st.textContent = style[1];
    document.getElementById('ag-d-source').classList.toggle('hidden', !r.is_walk_in);

    var phoneRow = document.getElementById('ag-d-phone-row');
    if (r.phone) {
      phoneRow.classList.remove('hidden');
      var pa = document.getElementById('ag-d-phone');
      pa.textContent = r.phone;
      pa.href = 'tel:' + r.phone;
    } else phoneRow.classList.add('hidden');

    setRow('ag-d-motif-row', !!r.motif);
    if (r.motif) document.getElementById('ag-d-motif').textContent = r.motif;

    var actesRow = document.getElementById('ag-d-actes-row');
    actesRow.innerHTML = '';
    if (r.actes && r.actes.length) {
      actesRow.classList.remove('hidden');
      r.actes.forEach(function (a) {
        var s = document.createElement('span');
        s.className = 'inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-700';
        s.textContent = a;
        actesRow.appendChild(s);
      });
    } else actesRow.classList.add('hidden');

    setRow('ag-d-devis-row', !!r.devis);
    if (r.devis) document.getElementById('ag-d-devis').textContent = r.devis;

    var hasTotal = r.total && r.total !== '0';
    document.getElementById('ag-d-total-row').classList.toggle('hidden', !hasTotal);
    if (hasTotal) document.getElementById('ag-d-total').textContent = Number(r.total).toLocaleString('fr-FR');

    setRow('ag-d-note-row', !!r.note);
    if (r.note) document.getElementById('ag-d-note-row').textContent = r.note;

    document.querySelectorAll('#ag-detail .ag-act').forEach(function (form) {
      form.action = (cfg.actionUrlTpl || '').replace('REF', r.ref);
      form.style.display = form.getAttribute('data-show') === r.status ? '' : 'none';
    });

    var rescheduleForm = document.getElementById('ag-d-reschedule');
    var slotInput = document.getElementById('ag-d-slot-input');
    if (rescheduleForm && slotInput) {
      var canMove = r.status === 'requested' || r.status === 'confirmed';
      rescheduleForm.classList.toggle('hidden', !canMove);
      if (canMove) {
        rescheduleForm.action = (cfg.updateUrlTpl || '').replace('REF', r.ref);
        slotInput.value = r.slot_iso || '';
      }
    }

    open(detailModal);
  }

  function isMovable(status) {
    return status === 'requested' || status === 'confirmed';
  }

  function dropTarget(el) {
    return el.closest('.ag-slot, .ag-free');
  }

  function clearDropHighlights() {
    document.querySelectorAll('.ag-slot.ag-drop-over, .ag-free.ag-drop-over').forEach(function (c) {
      c.classList.remove('ag-drop-over');
    });
  }

  function moveRdv(ref, slot) {
    var url = (cfg.moveUrlTpl || '').replace('REF', ref);
    var fd = new FormData();
    fd.append('csrfmiddlewaretoken', csrf());
    fd.append('slot', slot);

    fetch(url, { method: 'POST', body: fd, credentials: 'same-origin' })
      .then(function (res) { return res.json().then(function (j) { return { ok: res.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.j.ok) {
          toast(res.j.error || 'Déplacement impossible.', true);
          return;
        }
        toast('RDV déplacé — ' + res.j.label);
        window.setTimeout(function () { window.location.reload(); }, 400);
      })
      .catch(function () {
        toast('Erreur réseau.', true);
      });
  }

  function onDragStart(e) {
    var cell = e.currentTarget;
    dragRef = cell.getAttribute('data-rdv');
    cell.classList.add('is-dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragRef);
  }

  function onDragEnd(e) {
    e.currentTarget.classList.remove('is-dragging');
    dragRef = null;
    clearDropHighlights();
  }

  function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    var target = dropTarget(e.currentTarget);
    if (target) target.classList.add('ag-drop-over');
  }

  function onDragLeave(e) {
    var target = dropTarget(e.currentTarget);
    if (target) target.classList.remove('ag-drop-over');
  }

  function onDrop(e) {
    e.preventDefault();
    var target = dropTarget(e.currentTarget);
    if (!target) return;
    target.classList.remove('ag-drop-over');
    var ref = e.dataTransfer.getData('text/plain') || dragRef;
    var slot = target.getAttribute('data-slot');
    if (!ref || !slot) return;

    var fromCell = document.querySelector('.ag-rdv[data-rdv="' + ref + '"]');
    if (fromCell && fromCell.getAttribute('data-slot') === slot) return;

    moveRdv(ref, slot);
  }

  function bindRdvCell(cell) {
    var status = cell.getAttribute('data-status');
    if (isMovable(status)) {
      cell.setAttribute('draggable', 'true');
      cell.addEventListener('dragstart', onDragStart);
      cell.addEventListener('dragend', onDragEnd);
    } else {
      cell.classList.add('is-locked');
    }

    cell.addEventListener('click', function () {
      if (cell.classList.contains('is-dragging')) return;
      var r = data[cell.getAttribute('data-rdv')];
      if (r) showDetail(r);
    });
  }

  function bindFreeCell(cell) {
    cell.addEventListener('click', function () {
      if (dragRef) return;
      openAddModal(cell.getAttribute('data-slot'), cell.getAttribute('data-label'));
    });
  }

  function bindDropTarget(el) {
    el.addEventListener('dragover', onDragOver);
    el.addEventListener('dragleave', onDragLeave);
    el.addEventListener('drop', onDrop);
  }

  document.querySelectorAll('.ag-rdv').forEach(bindRdvCell);
  document.querySelectorAll('.ag-free').forEach(bindFreeCell);
  document.querySelectorAll('.ag-slot').forEach(bindDropTarget);
})();
