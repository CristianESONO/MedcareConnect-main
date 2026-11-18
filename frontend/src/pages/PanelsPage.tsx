import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { AlertCircle, Plus } from 'lucide-react';
import { PanelCard } from '../components/panels/PanelCard';
import { PanelBuilder } from '../components/panels/PanelBuilder';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import {
  panelsApi,
  practitionerPortalApi,
  type Panel,
  type ProviderPanelsData,
} from '../lib/api';

export function PanelsPage() {
  const load = useCallback((signal: AbortSignal) => panelsApi.list(signal), []);
  const [data, setData] = useState<ProviderPanelsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editing, setEditing] = useState<Panel | null>(null);
  const [sendPanel, setSendPanel] = useState<Panel | null>(null);
  const [sendTargets, setSendTargets] = useState<number[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal)
      .then((payload) => {
        setData(payload);
        setError('');
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : 'Impossible de charger les panels.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [load, refreshKey]);

  const reload = () => {
    setLoading(true);
    setRefreshKey((current) => current + 1);
  };

  const savePanel = async (panel: Omit<Panel, 'id'>) => {
    const body = new FormData();
    body.set('nom', panel.nom);
    body.set('description', panel.description);
    body.set('kind', panel.kind || 'panel');
    body.set('acte_ids', panel.actes.map((act) => String(act.id)).join(','));
    if (editing && !editing.is_prestation_ticket) body.set('panel_id', String(editing.id));
    const result = await panelsApi.create(body);
    setNotice(`« ${result.nom} » a été enregistré.`);
    setError('');
    setEditing(null);
    reload();
  };

  const closeBuilder = () => {
    setBuilderOpen(false);
    setEditing(null);
  };

  const editPanel = (panel: Panel) => {
    setEditing(panel);
    setBuilderOpen(true);
  };

  const deletePanel = async (id: number | string) => {
    if (!window.confirm('Confirmer la suppression de ce panel ?')) return;
    setError('');
    setNotice('');
    try {
      await panelsApi.delete(id);
      setNotice('Panel supprimé.');
      reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de supprimer ce panel.');
    }
  };

  const togglePanel = async (id: number | string) => {
    setError('');
    setNotice('');
    try {
      await panelsApi.toggle(id);
      setNotice('Statut du panel mis à jour.');
      reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible de modifier le statut.');
    }
  };

  const send = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sendPanel || sendTargets.length === 0) return;
    const body = new FormData();
    body.set(sendPanel.is_prestation_ticket ? 'ticket_nom' : 'panel_nom', sendPanel.nom);
    if (sendPanel.public_path) body.set(
      sendPanel.is_prestation_ticket ? 'ticket_url' : 'panel_url',
      new URL(sendPanel.public_path, window.location.origin).toString(),
    );
    if (sendPanel.token) body.set('panel_token', sendPanel.token);
    sendTargets.forEach((id) => body.append('conv_ids', String(id)));
    setSending(true);
    setError('');
    try {
      const result = sendPanel.is_prestation_ticket
        ? await practitionerPortalApi.sendTicket(body)
        : await panelsApi.send(body);
      setNotice(result.message);
      setSendPanel(null);
      setSendTargets([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Impossible d’envoyer ce lien.');
    } finally {
      setSending(false);
    }
  };

  const panels = data?.panels ?? [];
  const builderActs = data?.acts ?? [];

  return (
    <div className="mx-auto min-h-screen w-full max-w-7xl px-4 py-8">
      <header className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <span className="text-xs font-bold uppercase tracking-widest text-accent">Gestion des tarifs et forfaits</span>
          <h1 className="mt-1 text-2xl font-extrabold text-navy dark:text-white sm:text-3xl">Panels et tickets</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {data?.organization || 'Regroupez des actes médicaux exécutables et partagez les liens aux patients.'}
          </p>
        </div>
        <Button size="md" onClick={() => { setEditing(null); setBuilderOpen(true); }}>
          <Plus size={16} /><span>Nouveau panel</span>
        </Button>
      </header>

      <div className="mb-6 flex items-start gap-3 rounded-xl border border-accent/20 bg-accent/10 p-4 text-xs font-medium text-navy dark:text-accent">
        <AlertCircle size={18} className="mt-0.5 shrink-0" />
        <span>Seuls les actes médicaux élémentaires et exécutables (niveau 3) peuvent être ajoutés à un panel.</span>
      </div>

      {error && <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">{error}</p>}
      {notice && <p role="status" className="mb-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">{notice}</p>}

      {loading ? (
        <p className="py-12 text-center text-sm text-slate-500">Chargement des panels…</p>
      ) : (
        <>
          {panels.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center dark:border-slate-700">
              <p className="font-semibold">Aucun panel ou ticket pour le moment.</p>
              <p className="mt-1 text-sm text-slate-500">Créez un panel à partir des actes disponibles pour votre structure.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {panels.map((panel, index) => (
                <PanelCard
                  key={panel.id}
                  panel={panel}
                  index={index}
                  onEdit={panel.is_prestation_ticket ? undefined : editPanel}
                  onDelete={deletePanel}
                  onToggle={togglePanel}
                  onSend={setSendPanel}
                />
              ))}
            </div>
          )}
        </>
      )}

      {builderOpen && (
        <PanelBuilder
          key={editing ? String(editing.id) : 'new-panel'}
          open={builderOpen}
          onClose={closeBuilder}
          onSave={savePanel}
          availableActs={builderActs}
          initialPanel={editing}
        />
      )}

      <Modal open={Boolean(sendPanel)} onClose={() => { setSendPanel(null); setSendTargets([]); }} title={`Envoyer « ${sendPanel?.nom || ''} »`}>
        <form onSubmit={send} className="space-y-4">
          {data?.conversations.length ? (
            <div className="max-h-72 space-y-2 overflow-y-auto">
              {data.conversations.map((conversation) => (
                <label key={conversation.id} className="flex items-start gap-3 rounded-xl border border-slate-200 p-3 text-sm dark:border-slate-700">
                  <input
                    type="checkbox"
                    checked={sendTargets.includes(conversation.id)}
                    onChange={(event) => setSendTargets((current) => event.target.checked
                      ? [...current, conversation.id]
                      : current.filter((id) => id !== conversation.id))}
                  />
                  <span><strong className="block">{conversation.patient}</strong><span className="text-xs text-slate-500">{conversation.subject}</span></span>
                </label>
              ))}
            </div>
          ) : <p className="text-sm text-slate-500">Aucune conversation active pour l’envoi.</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" size="md" onClick={() => setSendPanel(null)}>Annuler</Button>
            <Button type="submit" size="md" disabled={!sendTargets.length || sending}>{sending ? 'Envoi…' : 'Envoyer le lien'}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
