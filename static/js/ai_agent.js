/**
 * Agent IA MedCare - Chatbot interactif & Recherche intelligente
 */
(function () {
  function initAiAgent() {
    const fabBtn = document.getElementById('mcAiFab');
    const modal = document.getElementById('mcAiModal');
    const closeBtn = document.getElementById('mcAiClose');
    const form = document.getElementById('mcAiForm');
    const input = document.getElementById('mcAiInput');
    const stream = document.getElementById('mcAiMessageStream');
    const typing = document.getElementById('mcAiTyping');
    const chatBody = document.getElementById('mcAiChatBody');

    if (!modal) return;

    const endpointUrl = '/sante/api/ai-agent/';
    let dragState = null;
    let suppressFabClick = false;

    function clampFabPosition(left, top) {
      if (!fabBtn) return { left, top };
      return {
        left: Math.max(0, Math.min(left, window.innerWidth - fabBtn.offsetWidth)),
        top: Math.max(0, Math.min(top, window.innerHeight - fabBtn.offsetHeight)),
      };
    }

    function placeFab(left, top) {
      if (!fabBtn) return;
      const position = clampFabPosition(left, top);
      fabBtn.style.left = `${position.left}px`;
      fabBtn.style.top = `${position.top}px`;
      fabBtn.style.right = 'auto';
      fabBtn.style.bottom = 'auto';
    }

    if (fabBtn) {
      fabBtn.addEventListener('pointerdown', function (event) {
        if (event.button !== 0) return;
        const rect = fabBtn.getBoundingClientRect();
        dragState = {
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          left: rect.left,
          top: rect.top,
          moved: false,
        };
        fabBtn.setPointerCapture(event.pointerId);
      });

      fabBtn.addEventListener('pointermove', function (event) {
        if (!dragState || dragState.pointerId !== event.pointerId) return;
        const deltaX = event.clientX - dragState.startX;
        const deltaY = event.clientY - dragState.startY;
        if (!dragState.moved && Math.hypot(deltaX, deltaY) < 6) return;

        dragState.moved = true;
        fabBtn.classList.add('is-dragging');
        placeFab(dragState.left + deltaX, dragState.top + deltaY);
        event.preventDefault();
      });

      function finishFabDrag(event) {
        if (!dragState || dragState.pointerId !== event.pointerId) return;
        if (dragState.moved) {
          suppressFabClick = true;
          fabBtn.classList.remove('is-dragging');
          setTimeout(() => { suppressFabClick = false; }, 0);
        }
        dragState = null;
      }

      fabBtn.addEventListener('pointerup', finishFabDrag);
      fabBtn.addEventListener('pointercancel', finishFabDrag);

      window.addEventListener('resize', function () {
        if (fabBtn.style.left && fabBtn.style.top) {
          const rect = fabBtn.getBoundingClientRect();
          placeFab(rect.left, rect.top);
        }
      });
    }

    function openModal() {
      modal.removeAttribute('hidden');
      modal.setAttribute('aria-hidden', 'false');
      modal.classList.add('is-open');
      if (fabBtn) fabBtn.classList.add('is-active');
      if (input) setTimeout(() => input.focus(), 150);
      scrollToBottom();
    }

    function closeModal() {
      modal.setAttribute('hidden', '');
      modal.setAttribute('aria-hidden', 'true');
      modal.classList.remove('is-open');
      if (fabBtn) fabBtn.classList.remove('is-active');
    }

    function toggleModal() {
      if (modal.hasAttribute('hidden')) {
        openModal();
      } else {
        closeModal();
      }
    }

    function scrollToBottom() {
      if (chatBody) {
        chatBody.scrollTop = chatBody.scrollHeight;
      }
    }

    function escapeHtml(str) {
      return (str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function formatMarkdownText(text) {
      let html = escapeHtml(text);
      html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
      html = html.replace(/\n/g, '<br>');
      return html;
    }

    function appendUserMessage(text) {
      if (!stream) return;
      const msgDiv = document.createElement('div');
      msgDiv.className = 'mc-ai-msg mc-ai-msg--user';
      msgDiv.innerHTML = `<div class="mc-ai-msg-content">${escapeHtml(text)}</div>`;
      stream.appendChild(msgDiv);
      scrollToBottom();
    }

    function appendBotResponse(data) {
      if (!stream) return;
      const msgDiv = document.createElement('div');
      msgDiv.className = 'mc-ai-msg mc-ai-msg--bot';

      let html = `<div class="mc-ai-msg-content">${formatMarkdownText(data.answer || '')}</div>`;

      if (data.results && data.results.length > 0) {
        html += `<div class="mc-ai-results-grid">`;
        data.results.forEach(res => {
          html += `
            <div class="mc-ai-card">
              <div class="mc-ai-card-top">
                <span class="mc-ai-card-badge mc-ai-card-badge--${res.type}">${escapeHtml(res.badge || res.type)}</span>
                <div class="mc-ai-card-title">${escapeHtml(res.title)}</div>
                <div class="mc-ai-card-cat">${escapeHtml(res.category)}</div>
              </div>
              <div class="mc-ai-card-detail">${escapeHtml(res.detail)}</div>
              <a href="${escapeHtml(res.url)}" class="mc-ai-card-act">
                <span>${escapeHtml(res.action_text || 'Voir sur Trouver un service')}</span>
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"/></svg>
              </a>
            </div>
          `;
        });
        html += `</div>`;
      }

      msgDiv.innerHTML = html;
      stream.appendChild(msgDiv);
      scrollToBottom();
    }

    function sendQuery(promptText) {
      const query = (promptText || '').trim();
      if (!query) return;

      appendUserMessage(query);
      if (input) input.value = '';

      if (typing) typing.removeAttribute('hidden');
      scrollToBottom();

      const csrfEl = document.querySelector('[name=csrfmiddlewaretoken]');
      const csrfToken = csrfEl ? csrfEl.value : '';

      fetch(endpointUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ prompt: query }),
      })
        .then(res => res.json())
        .then(data => {
          if (typing) typing.setAttribute('hidden', '');
          appendBotResponse(data);
        })
        .catch(err => {
          console.error('Erreur Agent IA:', err);
          if (typing) typing.setAttribute('hidden', '');
          appendBotResponse({
            answer: "Désolé, une erreur s'est produite lors du traitement de votre demande. Vous pouvez réessayer ou effectuer une recherche directe.",
            results: [],
          });
        });
    }

    // Global document click delegation
    document.addEventListener('click', function (e) {
      const target = e.target;
      if (!target || !target.closest) return;

      const fab = target.closest('#mcAiFab, .mc-fab-ai');
      if (fab) {
        e.preventDefault();
        if (suppressFabClick) return;
        toggleModal();
        return;
      }

      const close = target.closest('#mcAiClose, .mc-ai-close-btn');
      if (close) {
        e.preventDefault();
        closeModal();
        return;
      }

      const chip = target.closest('.mc-ai-chip');
      if (chip) {
        e.preventDefault();
        const q = chip.getAttribute('data-query');
        if (q) {
          if (modal.hasAttribute('hidden')) openModal();
          sendQuery(q);
        }
      }
    });

    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (input) sendQuery(input.value);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAiAgent);
  } else {
    initAiAgent();
  }
})();
