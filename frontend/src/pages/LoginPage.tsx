import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';

export function LoginPage() {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      navigate('/dashboard');
    }, 600);
  };

  const handleDemoLogin = (role: 'patient' | 'pro') => {
    if (role === 'patient') {
      setIdentifier('patient@medcare.sn');
      setPassword('medcare2026');
      setTimeout(() => navigate('/search'), 300);
    } else {
      setIdentifier('dr.diop@cliniquemadeleine.sn');
      setPassword('medcare2026');
      setTimeout(() => navigate('/dashboard'), 300);
    }
  };

  return (
    <div className="min-h-screen py-10 px-4 flex items-center justify-center bg-gray-50 dark:bg-[#0b1120]">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md bg-white dark:bg-gray-800 rounded-3xl shadow-xl border border-gray-200 dark:border-gray-700 p-6 sm:p-9"
      >
        {/* Brand */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-3">
            <img src="/logo.png" alt="MedCare" className="h-9 w-auto" />
            <span className="font-syne font-extrabold text-xl text-[#123a63] dark:text-white">
              MedCare<span className="text-[#0ea5e9]">Connect</span>
            </span>
          </Link>
          <h1 className="font-syne font-extrabold text-2xl text-gray-900 dark:text-white">
            Connexion
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
            Accédez à vos soins, devis ou espace praticien
          </p>
        </div>

        {/* Demo Fast Login Buttons */}
        <div className="mb-6 p-3 rounded-2xl bg-sky-50/70 dark:bg-sky-950/20 border border-sky-200/60 dark:border-sky-800/60">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#0284c7] block mb-2">
            🚀 Accès Démo Rapide
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleDemoLogin('patient')}
              className="py-1.5 px-2 rounded-xl bg-white dark:bg-gray-800 border border-sky-200 dark:border-gray-700 text-xs font-bold text-[#123a63] dark:text-sky-300 hover:bg-sky-50 dark:hover:bg-gray-700 transition-colors"
            >
              Mode Patient
            </button>
            <button
              type="button"
              onClick={() => handleDemoLogin('pro')}
              className="py-1.5 px-2 rounded-xl bg-white dark:bg-gray-800 border border-sky-200 dark:border-gray-700 text-xs font-bold text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-gray-700 transition-colors"
            >
              Mode Soignant
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1">
              Email ou Téléphone (+221) *
            </label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400">
                <i className="ti ti-user text-base"></i>
              </span>
              <input
                type="text"
                required
                placeholder="nom@exemple.sn ou 77..."
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                Mot de passe *
              </label>
              <a href="#forgot" className="text-[11px] font-semibold text-[#0ea5e9] hover:underline">
                Oublié ?
              </a>
            </div>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400">
                <i className="ti ti-lock text-base"></i>
              </span>
              <input
                type={showPassword ? 'text' : 'password'}
                required
                placeholder="Votre mot de passe"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0ea5e9]/40"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'} text-base`}></i>
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#123a63] to-[#0ea5e9] text-white font-bold text-sm shadow-md hover:shadow-lg transition-all active:scale-[0.99] flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <>
                <i className="ti ti-login text-base"></i>
                <span>Se connecter</span>
              </>
            )}
          </button>

          <div className="text-center text-xs text-gray-500 pt-3 border-t border-gray-200 dark:border-gray-700">
            Pas encore de compte ?{' '}
            <Link to="/register" className="font-bold text-[#123a63] dark:text-[#0ea5e9] hover:underline">
              Inscrivez-vous ici
            </Link>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
