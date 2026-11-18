import { useEffect, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { adminDashboardApi, type AdminPlatformReview } from '../lib/api';
import { AdminDashboardShell } from './AdminDashboardPage';

export function AdminReviewsPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status') || 'all';
  const page = Math.max(1, Number(searchParams.get('page') || 1));
  const [reviews, setReviews] = useState<AdminPlatformReview[]>([]);
  const [counts, setCounts] = useState({ all: 0, pending: 0, approved: 0 });
  const [pagination, setPagination] = useState<{ page: number; pages: number; total: number; has_previous: boolean; has_next: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    adminDashboardApi.reviews({ status: status === 'all' ? '' : status, page }, controller.signal)
      .then((response) => {
        setReviews(response.rows);
        setCounts(response.counts);
        setPagination(response.pagination);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Impossible de charger les avis.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, status]);

  const act = async (review: AdminPlatformReview, action: 'approve' | 'delete') => {
    if (action === 'delete' && !window.confirm('Supprimer définitivement cet avis ?')) return;
    setBusyId(review.id);
    setError('');
    setNotice('');
    try {
      await adminDashboardApi.reviewAction(review.id, action);
      setNotice(action === 'approve' ? 'Avis approuvé et notification envoyée.' : 'Avis supprimé.');
      setReviews((previous) => action === 'delete' || (action === 'approve' && status === 'pending')
        ? previous.filter((item) => item.id !== review.id)
        : previous.map((item) => item.id === review.id ? { ...item, is_approved: true } : item));
      setCounts((current) => ({
        ...current,
        all: Math.max(0, current.all - (action === 'delete' ? 1 : 0)),
        pending: Math.max(0, current.pending - (!review.is_approved ? 1 : 0)),
        approved: Math.max(0, current.approved + (action === 'approve' && !review.is_approved ? 1 : action === 'delete' && review.is_approved ? -1 : 0)),
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de traiter cet avis.');
    } finally {
      setBusyId(null);
    }
  };

  const authError = error.toLowerCase().includes('authentification') || error.toLowerCase().includes('accès réservé');

  return (
    <AdminDashboardShell active="/dashboard/avis/">
      <header className="mb-5">
        <p className="text-xs font-bold uppercase tracking-widest text-sky-700">Modération</p>
        <h1 className="mt-1 font-syne text-2xl font-extrabold">Avis plateforme</h1>
      </header>
      {notice && <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}{authError && <Link to={`/connexion/?next=${encodeURIComponent(location.pathname)}`} className="ml-2 underline">Se connecter</Link>}</p>}
      <nav className="mb-4 flex gap-2" aria-label="Filtrer les avis">
        {[
          ['all', `Tous (${counts.all})`],
          ['pending', `En attente (${counts.pending})`],
          ['approved', `Approuvés (${counts.approved})`],
        ].map(([value, label]) => <Link key={value} to={value === 'all' ? '/dashboard/avis/' : `/dashboard/avis/?status=${value}`} aria-current={status === value ? 'page' : undefined} className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${status === value ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700'}`}>{label}</Link>)}
      </nav>
      {loading && <p className="rounded-xl bg-white p-5 text-sm text-slate-500" role="status">Chargement…</p>}
      {!loading && (
        <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="p-3">Patient</th><th className="p-3">Note</th><th className="p-3">Actes</th><th className="p-3">Commentaire</th><th className="p-3">État / date</th><th className="p-3">Actions</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {reviews.map((review) => <tr key={review.id}>
                <td className="p-3 font-semibold">{review.patient}<small className="block text-xs font-normal text-slate-500">{review.patient_email}</small></td>
                <td className="p-3 font-bold">{'★'.repeat(review.rating)}{'☆'.repeat(5 - review.rating)}</td>
                <td className="p-3">{review.actes.length ? review.actes.join(', ') : '—'}</td>
                <td className="max-w-sm p-3 text-slate-700">{review.comment || '—'}</td>
                <td className="p-3">{review.is_approved ? 'Approuvé' : 'En attente'}<small className="block text-xs text-slate-500">{new Date(review.created_at).toLocaleDateString('fr-FR')}</small></td>
                <td className="p-3"><div className="flex flex-col items-start gap-2">{!review.is_approved && <button type="button" disabled={busyId === review.id} onClick={() => void act(review, 'approve')} className="text-xs font-semibold text-emerald-800 disabled:opacity-50">Approuver</button>}<button type="button" disabled={busyId === review.id} onClick={() => void act(review, 'delete')} className="text-xs font-semibold text-red-700 disabled:opacity-50">Supprimer</button></div></td>
              </tr>)}
              {!reviews.length && <tr><td colSpan={6} className="p-8 text-center text-slate-500">Aucun avis dans cette catégorie.</td></tr>}
            </tbody>
          </table>
          {pagination && pagination.pages > 1 && <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600"><span>{pagination.total} avis · page {pagination.page}/{pagination.pages}</span><div className="flex gap-2"><Link aria-disabled={!pagination.has_previous} to={`/dashboard/avis/?${new URLSearchParams({ ...(status !== 'all' ? { status } : {}), page: String(Math.max(1, page - 1)) })}`} className={`rounded border px-3 py-1.5 ${pagination.has_previous ? 'bg-white' : 'pointer-events-none opacity-40'}`}>Précédent</Link><Link aria-disabled={!pagination.has_next} to={`/dashboard/avis/?${new URLSearchParams({ ...(status !== 'all' ? { status } : {}), page: String(page + 1) })}`} className={`rounded border px-3 py-1.5 ${pagination.has_next ? 'bg-white' : 'pointer-events-none opacity-40'}`}>Suivant</Link></div></div>}
        </section>
      )}
    </AdminDashboardShell>
  );
}
