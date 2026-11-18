import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { FavoriteButton } from '../components/FavoriteButton';
import { discoveryApi, type FavoriteEntry } from '../lib/api';

export function FavoritesPage() {
  const [favorites, setFavorites] = useState<FavoriteEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    discoveryApi.favorites(controller.signal)
      .then((data) => setFavorites(data.favorites))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger vos favoris.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-8">
      <header className="mb-6">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Espace patient</p>
        <h1 className="mt-1 flex items-center gap-2 font-syne text-2xl font-extrabold text-[#123a63] sm:text-3xl"><Heart size={23} /> Mes favoris</h1>
      </header>
      {loading && <p className="rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement de vos favoris…</p>}
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-800" role="alert">{error}{error.includes('Authentification') && <a href={`/connexion/?next=${encodeURIComponent('/sante/favoris/')}`} className="ml-2 font-bold underline">Se connecter</a>}</p>}
      {!loading && !error && favorites.length === 0 && (
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="font-semibold text-gray-700">Aucun favori pour le moment</p>
          <p className="mt-1 text-sm text-gray-500">Ajoutez des structures depuis l’annuaire pour les retrouver ici.</p>
          <Link to="/sante/annuaire/" className="mt-4 inline-flex rounded-lg bg-[#0a5c8a] px-4 py-2 text-sm font-bold text-white">Ouvrir l’annuaire</Link>
        </div>
      )}
      {!loading && favorites.length > 0 && (
        <div className="space-y-3">
          {favorites.map((favorite) => (
            <article key={favorite.id} className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center">
              {favorite.logo ? <img src={favorite.logo} alt="" className="size-14 rounded-xl object-cover" /> : <span className="size-14 rounded-xl bg-sky-50" />}
              <div className="min-w-0 flex-1">
                <h2 className="font-bold text-[#123a63]">{favorite.name}</h2>
                <p className="mt-1 text-xs text-gray-500">{[favorite.type, favorite.quartier, favorite.city].filter(Boolean).join(' · ')}</p>
              </div>
              <Link to={favorite.profile_url} className="rounded-lg bg-[#0a5c8a] px-4 py-2 text-center text-xs font-bold text-white">Voir la fiche</Link>
              <FavoriteButton
                slug={favorite.slug}
                initialFavorite
                onChange={(isFavorite) => {
                  if (!isFavorite) setFavorites((current) => current.filter((entry) => entry.id !== favorite.id));
                }}
              />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
