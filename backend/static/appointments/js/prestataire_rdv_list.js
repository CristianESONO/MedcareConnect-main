/**
 * Liste RDV prestataire — modale de modification (créneau, walk-in, note).
 */
(function () {
  'use strict';

  var modal = document.getElementById('rdv-edit-modal');
  var form = document.getElementById('rdv-edit-form');
  if (!modal || !form) return;

  var slotInput = document.getElementById('rdv-edit-slot');
  var refLabel = document.getElementById('rdv-edit-ref');
  var walkinBlock = document.getElementById('rdv-edit-walkin');
  var nameInput = document.getElementById('rdv-edit-name');
  var phoneInput = document.getElementById('rdv-edit-phone');
  var motifInput = document.getElementById('rdv-edit-motif');
  var noteInput = document.getElementById('rdv-edit-note');
  var statusInput = document.getElementById('rdv-edit-status');

  function openModal(btn) {
    form.action = btn.getAttribute('data-url');
    if (refLabel) refLabel.textContent = btn.getAttribute('data-ref') || '';
    if (slotInput) slotInput.value = btn.getAttribute('data-slot') || '';
    if (statusInput) statusInput.value = btn.getAttribute('data-status-filter') || 'upcoming';
    if (noteInput) noteInput.value = btn.getAttribute('data-note') || '';

    var isWalkIn = btn.getAttribute('data-walk-in') === '1';
    if (walkinBlock) walkinBlock.classList.toggle('hidden', !isWalkIn);
    if (isWalkIn) {
      if (nameInput) {
        nameInput.value = btn.getAttribute('data-name') || '';
        nameInput.required = true;
      }
      if (phoneInput) phoneInput.value = btn.getAttribute('data-phone') || '';
      if (motifInput) motifInput.value = btn.getAttribute('data-motif') || '';
    } else if (nameInput) {
      nameInput.required = false;
    }

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    modal.setAttribute('aria-hidden', 'false');
    if (slotInput) slotInput.focus();
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    modal.setAttribute('aria-hidden', 'true');
  }

  document.querySelectorAll('.rdv-edit-open').forEach(function (btn) {
    btn.addEventListener('click', function () { openModal(btn); });
  });

  document.querySelectorAll('.rdv-edit-close').forEach(function (btn) {
    btn.addEventListener('click', closeModal);
  });

  modal.addEventListener('click', function (e) {
    if (e.target === modal) closeModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeModal();
  });
})();
