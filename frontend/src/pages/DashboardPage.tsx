import { motion } from 'framer-motion';
import { Users, DollarSign, Activity, FileCheck, Calendar, Bell } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { StatCard } from '../components/dashboard/StatCard';
import { ActivityChart } from '../components/dashboard/ActivityChart';
import { CompletionBar } from '../components/dashboard/CompletionBar';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';

const MOCK_ACTIVITY = [
  { label: 'Lun', value: 14 },
  { label: 'Mar', value: 22 },
  { label: 'Mer', value: 18 },
  { label: 'Jeu', value: 27 },
  { label: 'Ven', value: 31 },
  { label: 'Sam', value: 19 },
  { label: 'Dim', value: 8 },
];

export function DashboardPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen py-8 px-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <span className="text-xs font-bold text-accent uppercase tracking-widest">
            Espace Prestataire de Santé
          </span>
          <h1 className="font-syne font-extrabold text-2xl sm:text-3xl text-navy dark:text-white mt-1">
            Tableau de Bord & Activité
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
            Suivi en temps réel de vos actes, devis et patients
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm">
            <Calendar size={15} />
            <span>Ce mois-ci</span>
          </Button>
          <Button size="sm">
            <Bell size={15} />
            <span>Notifications</span>
          </Button>
        </div>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title={t('dashboard.patients')}
          value="142"
          subtitle="+18% par rapport au mois dernier"
          icon={<Users size={20} />}
          trend={{ value: 18, isPositive: true }}
          index={0}
        />
        <StatCard
          title={t('dashboard.revenue')}
          value="4 850 000 FCFA"
          subtitle="Total devis validés"
          icon={<DollarSign size={20} />}
          trend={{ value: 12, isPositive: true }}
          index={1}
        />
        <StatCard
          title={t('dashboard.actes')}
          value="318"
          subtitle="Actes médicaux enregistrés"
          icon={<Activity size={20} />}
          trend={{ value: 6, isPositive: true }}
          index={2}
        />
        <StatCard
          title={t('dashboard.completion')}
          value="92%"
          subtitle="Profil et grille tarifaire"
          icon={<FileCheck size={20} />}
          index={3}
        />
      </div>

      {/* Grid: Activity Chart + Profile completion */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityChart data={MOCK_ACTIVITY} title="Volume des consultations de la semaine" />
        </div>

        <div>
          <Card className="p-5 flex flex-col justify-between h-full">
            <div>
              <h3 className="font-syne font-bold text-navy dark:text-white text-base mb-4">
                Complétude du Profil
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-5 leading-relaxed">
                Un profil à 100% augmente la visibilité de votre structure dans les résultats de recherche SIPN.
              </p>

              <div className="flex flex-col gap-4">
                <CompletionBar label="Grille des Tarifs" percentage={100} color="bg-sipn-green" />
                <CompletionBar label="Conventionnement Assurances" percentage={85} color="bg-accent" />
                <CompletionBar label="Horaires d'Ouverture" percentage={90} color="bg-accent" />
                <CompletionBar label="Panels & Forfaits" percentage={75} color="bg-amber-500" />
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700/60">
              <Button variant="secondary" size="sm" className="w-full">
                Mettre à jour le profil
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
