/**
 * Agent IA MedCare - Chatbot interactif & Recherche intelligente
 */
document.addEventListener('DOMContentLoaded', function () {
  const fabBtn = document.getElementById('mcAiFab');
  const modal = document.getElementById('mcAiModal');
  const closeBtn = document.getElementById('mcAiClose');
  const form = document.getElementById('mcAiForm');
  const input = document.getElementById('mcAiInput');
  const stream = document.getElementById('mcAiMessageStream');
  const typing = document.getElementById('mcAiTyping');
  const chatBody = document.getElementById('mcAiChatBody');
  const chips = document.querySelectorAll('.mc-ai-chip');

  if (!fabBtn || !modal) return;

  const endpointUrl = '/healthcare/api/ai-agent/';

  function openModal() {
    modal.removeAttribute('hidden');
    modal.setAttribute('aria-hidden', 'false');
    modal.classList.add('is-open');
    fabBtn.classList.add('is-active');
    setTimeout(() => input.focus(), 150);
    scrollToBottom();
  }

  function closeModal() {
    modal.setAttribute('hidden', '');
    modal.setAttribute('aria-hidden', 'true');
    modal.classList.remove('is-open');
    fabBtn.classList.remove('is-active');
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
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function appendUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'mc-ai-msg mc-ai-msg--user';
    msgDiv.innerHTML = `<div class="mc-ai-msg-content">${escapeHtml(text)}</div>`;
    stream.appendChild(msgDiv);
    scrollToBottom();
  }

  function appendBotResponse(data) {
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
    const query = (promptText || '').strip ? promptText.strip() : (promptText || '').trim();
    if (!query) return;

    appendUserMessage(query);
    if (input) input.value = '';

    // Show typing
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

  // Event Listeners
  fabBtn.addEventListener('click', toggleModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      sendQuery(input.value);
    });
  }

  chips.forEach(chip => {
    chip.addEventListener('click', function () {
      const q = this.getAttribute('data-query');
      if (q) {
        if (modal.hasAttribute('hidden')) openModal();
        sendQuery(q);
      }
    });
  });
});
