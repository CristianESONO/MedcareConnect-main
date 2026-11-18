import { useEffect, useState } from 'react';
import { GuestCartPage } from './GuestCartPage';
import { PatientCartPage } from './PatientCartPage';
import { cartApi } from '../lib/api';

export function CartRoutePage({ onCartChange }: { onCartChange: () => Promise<void> }) {
  const [session, setSession] = useState<{ authenticated: boolean; is_patient: boolean } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    cartApi.session(controller.signal)
      .then(setSession)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de vérifier la session.');
        }
      });
    return () => controller.abort();
  }, []);

  if (error) {
    return <p className="mx-auto mt-8 max-w-3xl rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>;
  }
  if (!session) {
    return <p className="mx-auto mt-8 max-w-3xl rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-600" role="status">Chargement…</p>;
  }
  if (!session.authenticated) {
    return <GuestCartPage onCartChange={onCartChange} />;
  }
  if (session.is_patient) {
    return <PatientCartPage onCartChange={onCartChange} />;
  }
  return <PatientCartPage onCartChange={onCartChange} accountMode />;
}
