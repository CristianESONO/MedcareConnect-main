import { useState } from 'react';
import { Heart } from 'lucide-react';
import { discoveryApi } from '../lib/api';

export function FavoriteButton({
  slug,
  initialFavorite,
  className = '',
  onChange,
}: {
  slug: string;
  initialFavorite: boolean;
  className?: string;
  onChange?: (favorite: boolean) => void;
}) {
  const [favorite, setFavorite] = useState(initialFavorite);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const toggle = async () => {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await discoveryApi.toggleFavorite(slug);
      setFavorite(result.is_favorite);
      onChange?.(result.is_favorite);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : '';
      if (message.includes('Authentification')) {
        window.location.assign(`/connexion/?next=${encodeURIComponent(window.location.pathname)}`);
      } else {
        setError(message || 'Impossible de modifier ce favori.');
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <span className="inline-flex flex-col items-center">
      <button
        type="button"
        onClick={() => void toggle()}
        disabled={busy}
        aria-pressed={favorite}
        aria-label={favorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
        className={`inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:border-rose-200 hover:text-rose-700 disabled:opacity-50 ${className}`}
      >
        <Heart size={15} fill={favorite ? 'currentColor' : 'none'} aria-hidden="true" />
        {favorite ? 'Favori' : 'Ajouter aux favoris'}
      </button>
      {error && <span className="mt-1 text-[10px] text-red-700" role="alert">{error}</span>}
    </span>
  );
}
