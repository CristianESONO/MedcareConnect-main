import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent } from 'react';
import { getCsrfToken } from '../lib/auth';

type WidgetPosition = { x: number; y: number };
type DragState = WidgetPosition & {
  pointerId: number;
  startX: number;
  startY: number;
  didMove: boolean;
};

type AiResult = {
  type: string;
  title: string;
  category: string;
  detail: string;
  url: string;
  action_text?: string;
  badge?: string;
};

type AiMessage = {
  role: 'assistant' | 'user';
  text: string;
  results?: AiResult[];
  suggestions?: string[];
};

type AiResponse = {
  answer: string;
  results: AiResult[];
  suggested_chips: string[];
};

const INITIAL_SUGGESTIONS = [
  'Échographie',
  'Biologie médicale',
  'Radiologie & Scanner',
  'Urgence Ambulance',
];
const POSITION_STORAGE_KEY = 'medcare.ai-assistant.position.v1';
const WIDGET_SIZE = 58;
const MOBILE_WIDGET_SIZE = 50;
const VIEWPORT_GUTTER = 12;

function getWidgetSize() {
  return window.matchMedia('(max-width: 768px)').matches ? MOBILE_WIDGET_SIZE : WIDGET_SIZE;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function positionFromRatios(position: WidgetPosition): WidgetPosition {
  const size = getWidgetSize();
  const maxX = Math.max(VIEWPORT_GUTTER, window.innerWidth - size - VIEWPORT_GUTTER);
  const maxY = Math.max(VIEWPORT_GUTTER, window.innerHeight - size - VIEWPORT_GUTTER);
  return {
    x: clamp(position.x, 0, 1) * maxX,
    y: clamp(position.y, 0, 1) * maxY,
  };
}

function getInitialPosition(): WidgetPosition {
  const mobile = window.matchMedia('(max-width: 768px)').matches;
  const size = getWidgetSize();
  const maxY = Math.max(VIEWPORT_GUTTER, window.innerHeight - size - VIEWPORT_GUTTER);
  const bottomOffset = mobile ? 82 : 24;
  return {
    x: mobile ? 1 : 0,
    y: clamp((window.innerHeight - size - bottomOffset) / maxY, 0, 1),
  };
}

function readStoredPosition(): WidgetPosition {
  try {
    const stored = window.localStorage.getItem(POSITION_STORAGE_KEY);
    if (stored) {
      const position = JSON.parse(stored) as WidgetPosition;
      if (Number.isFinite(position.x) && Number.isFinite(position.y)) {
        return { x: clamp(position.x, 0, 1), y: clamp(position.y, 0, 1) };
      }
    }
  } catch (error) {
    console.error('Impossible de restaurer la position de l’assistant MedCare:', error);
  }
  return getInitialPosition();
}

function renderAnswer(text: string) {
  return text.split(/(\*\*.*?\*\*|\*.*?\*)/g).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={index}>{part.slice(1, -1)}</em>;
    }
    return <span key={index}>{part}</span>;
  });
}

export function AiAssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [position, setPosition] = useState<WidgetPosition>(readStoredPosition);
  const [panelPosition, setPanelPosition] = useState<WidgetPosition>({ x: VIEWPORT_GUTTER, y: VIEWPORT_GUTTER });
  const [isDragging, setIsDragging] = useState(false);
  const [messages, setMessages] = useState<AiMessage[]>([
    {
      role: 'assistant',
      text: 'Bonjour ! Je suis l’Assistant MedCare. Comment puis-je vous aider ?',
      suggestions: INITIAL_SUGGESTIONS,
    },
  ]);
  const inputRef = useRef<HTMLInputElement>(null);
  const chatBodyRef = useRef<HTMLDivElement>(null);
  const fabRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const suppressClickRef = useRef(false);

  const widgetPosition = positionFromRatios(position);

  const savePosition = (nextPosition: WidgetPosition) => {
    const size = getWidgetSize();
    const maxX = Math.max(VIEWPORT_GUTTER, window.innerWidth - size - VIEWPORT_GUTTER);
    const maxY = Math.max(VIEWPORT_GUTTER, window.innerHeight - size - VIEWPORT_GUTTER);
    const ratios = {
      x: clamp(nextPosition.x / maxX, 0, 1),
      y: clamp(nextPosition.y / maxY, 0, 1),
    };
    setPosition(ratios);
    try {
      window.localStorage.setItem(POSITION_STORAGE_KEY, JSON.stringify(ratios));
    } catch (error) {
      console.error('Impossible de mémoriser la position de l’assistant MedCare:', error);
    }
  };

  const handlePointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      ...widgetPosition,
      didMove: false,
    };
    suppressClickRef.current = false;
  };

  const handlePointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - drag.startX;
    const deltaY = event.clientY - drag.startY;
    if (!drag.didMove && Math.hypot(deltaX, deltaY) < 5) return;

    drag.didMove = true;
    suppressClickRef.current = true;
    setIsDragging(true);
    const size = getWidgetSize();
    const maxX = Math.max(VIEWPORT_GUTTER, window.innerWidth - size - VIEWPORT_GUTTER);
    const maxY = Math.max(VIEWPORT_GUTTER, window.innerHeight - size - VIEWPORT_GUTTER);
    const next = {
      x: clamp(drag.x + deltaX, VIEWPORT_GUTTER, maxX),
      y: clamp(drag.y + deltaY, VIEWPORT_GUTTER, maxY),
    };
    setPosition({ x: next.x / maxX, y: next.y / maxY });
  };

  const handlePointerUp = (event: PointerEvent<HTMLButtonElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (drag.didMove) {
      const rect = event.currentTarget.getBoundingClientRect();
      const size = getWidgetSize();
      const maxX = Math.max(VIEWPORT_GUTTER, window.innerWidth - size - VIEWPORT_GUTTER);
      const maxY = Math.max(VIEWPORT_GUTTER, window.innerHeight - size - VIEWPORT_GUTTER);
      const snappedX = rect.left + size / 2 < window.innerWidth / 2 ? VIEWPORT_GUTTER : maxX;
      savePosition({
        x: snappedX,
        y: clamp(rect.top, VIEWPORT_GUTTER, maxY),
      });
    }
    dragRef.current = null;
    setIsDragging(false);
  };

  const handleClick = () => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      return;
    }
    setIsOpen((open) => !open);
  };

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLButtonElement>) => {
    const directions: Record<string, WidgetPosition> = {
      ArrowLeft: { x: -16, y: 0 },
      ArrowRight: { x: 16, y: 0 },
      ArrowUp: { x: 0, y: -16 },
      ArrowDown: { x: 0, y: 16 },
    };
    const direction = directions[event.key];
    if (!direction) return;
    event.preventDefault();
    const size = getWidgetSize();
    const maxX = Math.max(VIEWPORT_GUTTER, window.innerWidth - size - VIEWPORT_GUTTER);
    const maxY = Math.max(VIEWPORT_GUTTER, window.innerHeight - size - VIEWPORT_GUTTER);
    savePosition({
      x: clamp(widgetPosition.x + direction.x, VIEWPORT_GUTTER, maxX),
      y: clamp(widgetPosition.y + direction.y, VIEWPORT_GUTTER, maxY),
    });
  };

  useEffect(() => {
    if (!isOpen) return undefined;
    inputRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useLayoutEffect(() => {
    if (!isOpen || !fabRef.current || !panelRef.current) return;
    const updatePanelPosition = () => {
      const button = fabRef.current?.getBoundingClientRect();
      const panel = panelRef.current;
      if (!button || !panel) return;
      const panelWidth = panel.getBoundingClientRect().width;
      const panelHeight = panel.getBoundingClientRect().height;
      const x = clamp(button.left, VIEWPORT_GUTTER, window.innerWidth - panelWidth - VIEWPORT_GUTTER);
      const above = button.top - panelHeight - VIEWPORT_GUTTER;
      const below = button.bottom + VIEWPORT_GUTTER;
      const y = above >= VIEWPORT_GUTTER
        ? above
        : clamp(below, VIEWPORT_GUTTER, window.innerHeight - panelHeight - VIEWPORT_GUTTER);
      setPanelPosition({ x, y });
    };
    updatePanelPosition();
    window.addEventListener('resize', updatePanelPosition);
    return () => window.removeEventListener('resize', updatePanelPosition);
  }, [isOpen, position]);

  const sendQuery = async (value: string) => {
    const prompt = value.trim();
    if (!prompt || isLoading) return;

    setQuery('');
    setMessages((current) => [...current, { role: 'user', text: prompt }]);
    setIsLoading(true);

    try {
      const csrfToken = await getCsrfToken();
      const response = await fetch('/sante/api/ai-agent/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ prompt }),
      });
      if (!response.ok) {
        throw new Error(`L’assistant a répondu avec le statut ${response.status}.`);
      }

      const data = await response.json() as AiResponse;
      setMessages((current) => [...current, {
        role: 'assistant',
        text: data.answer,
        results: data.results,
        suggestions: data.suggested_chips,
      }]);
    } catch (error) {
      console.error('Erreur de l’assistant IA MedCare:', error);
      setMessages((current) => [...current, {
        role: 'assistant',
        text: 'Désolé, l’assistant est momentanément indisponible. Réessayez ou lancez une recherche directement.',
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendQuery(query);
  };

  return (
    <>
      <button
        ref={fabRef}
        type="button"
        className={`mc-fab-ai${isDragging ? ' is-dragging' : ''}`}
        style={{ left: widgetPosition.x, top: widgetPosition.y }}
        data-docked={position.x >= 0.5 ? 'right' : 'left'}
        aria-label={isOpen ? 'Assistant IA MedCare ouvert' : 'Ouvrir l’assistant IA MedCare'}
        aria-description="Déplacez ce bouton pour le positionner à votre convenance."
        aria-keyshortcuts="ArrowUp ArrowDown ArrowLeft ArrowRight"
        aria-expanded={isOpen}
        aria-controls="mcAiModal"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
      >
        <span className="mc-fab-ai-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3v2m0 14v2M5.64 5.64l1.42 1.42m9.88 9.88 1.42 1.42M3 12h2m14 0h2M5.64 18.36l1.42-1.42m9.88-9.88 1.42-1.42" />
            <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" />
          </svg>
        </span>
        <span className="mc-fab-ai-badge" aria-hidden="true">IA</span>
        <span className="mc-fab-ai-tooltip" aria-hidden="true">Glisser pour déplacer · Assistant IA</span>
      </button>

      {isOpen && (
        <section
          ref={panelRef}
          id="mcAiModal"
          className="mc-ai-modal"
          style={{
            left: panelPosition.x,
            top: panelPosition.y,
            right: 'auto',
            bottom: 'auto',
            width: 'min(380px, calc(100vw - 24px))',
            height: 'min(520px, calc(100dvh - 24px))',
            maxHeight: 'none',
            boxSizing: 'border-box',
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="mcAiTitle"
        >
          <header className="mc-ai-modal-head">
            <div className="mc-ai-agent-identity">
              <span className="mc-ai-agent-avatar" aria-hidden="true">✦</span>
              <span>
                <span className="mc-ai-agent-name" id="mcAiTitle">Assistant IA MedCare</span>
                <span className="mc-ai-agent-sub">Recherche intelligente</span>
              </span>
            </div>
            <button
              type="button"
              className="mc-ai-close-btn"
              aria-label="Fermer l’assistant IA"
              onClick={() => setIsOpen(false)}
            >
              ×
            </button>
          </header>

          <div className="mc-ai-modal-body" ref={chatBodyRef} aria-live="polite">
            {messages.map((message, index) => (
              <div className={`mc-ai-msg mc-ai-msg--${message.role === 'user' ? 'user' : 'bot'}`} key={`${index}-${message.role}`}>
                <div className="mc-ai-msg-content">{renderAnswer(message.text)}</div>
                {message.results && message.results.length > 0 && (
                  <div className="mc-ai-results-grid">
                    {message.results.map((result, resultIndex) => (
                      <article className="mc-ai-card" key={`${result.title}-${resultIndex}`}>
                        <div className="mc-ai-card-top">
                          <span className="mc-ai-card-badge">{result.badge || result.type}</span>
                          <div className="mc-ai-card-title">{result.title}</div>
                          <div className="mc-ai-card-cat">{result.category}</div>
                        </div>
                        <div className="mc-ai-card-detail">{result.detail}</div>
                        <a className="mc-ai-card-act" href={result.url}>
                          {result.action_text || 'Voir les résultats'}
                          <span aria-hidden="true">→</span>
                        </a>
                      </article>
                    ))}
                  </div>
                )}
                {message.suggestions && (
                  <div className="mc-ai-chips">
                    {message.suggestions.map((suggestion) => (
                      <button
                        type="button"
                        className="mc-ai-chip"
                        key={suggestion}
                        disabled={isLoading}
                        onClick={() => void sendQuery(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="mc-ai-typing" role="status">
                <span className="mc-ai-typing-dot" />
                <span className="mc-ai-typing-dot" />
                <span className="mc-ai-typing-dot" />
                <span className="mc-ai-typing-lbl">MedCare réfléchit…</span>
              </div>
            )}
          </div>

          <form className="mc-ai-modal-foot" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="mcAiInput">Votre question</label>
            <input
              id="mcAiInput"
              className="mc-ai-input"
              ref={inputRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ex. échographie à Dakar…"
              autoComplete="off"
              disabled={isLoading}
            />
            <button
              type="submit"
              className="mc-ai-send-btn"
              aria-label="Envoyer la question"
              disabled={isLoading || !query.trim()}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="m22 2-7 20-4-9-9-4Z" />
                <path d="M22 2 11 13" />
              </svg>
            </button>
          </form>
        </section>
      )}
    </>
  );
}
