import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getCsrfToken } from '../lib/auth';

interface LoginPageProps {
  adminLogin?: (username: string, password: string) => Promise<void>;
}

export function LoginPage({ adminLogin }: LoginPageProps = {}) {
  const location = useLocation();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (adminLogin) {
        await adminLogin(identifier, password);
        return;
      }

      const csrfToken = await getCsrfToken();
      const formData = new URLSearchParams({ username: identifier, password });
      const next = new URLSearchParams(location.search).get('next');
      if (next) formData.set('next', next);

      const response = await fetch('/api/auth/login/', {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
          'X-CSRFToken': csrfToken,
        },
        body: formData,
      });
      const data = (await response.json()) as {
        redirect_url?: string;
        errors?: Record<string, string[]>;
      };
      if (!response.ok) {
        setError(Object.values(data.errors || {}).flat().join(' '));
      } else if (data.redirect_url) {
        window.location.assign(data.redirect_url);
      } else {
        throw new Error('Le serveur n’a pas indiqué la page de destination.');
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Une erreur inattendue a empêché la connexion.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mc-page-wrap">
      <section className="mc-auth-section">
        <div className="mc-container">
          <div className="mc-auth-card">
            <div className="mc-auth-header">
              <h1>Connexion</h1>
              <p>{adminLogin ? 'Accédez à l’administration MedCare Connect' : 'Accédez à votre espace MedCare Connect'}</p>
            </div>
            <form onSubmit={handleSubmit}>
          {error && (
            <div role="alert" className="mc-form-error">
              {error}
            </div>
          )}
          <div className="mc-form-group">
            <label className="mc-form-label" htmlFor="username">
              Nom d'utilisateur
            </label>
            <input
              id="username"
              type="text"
              required
              placeholder="Votre nom d'utilisateur"
              autoComplete="username"
              autoFocus
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="mc-form-input"
            />
          </div>

          <div className="mc-form-group">
            <label className="mc-form-label" htmlFor="password">Mot de passe</label>
            <div className="mc-password-field">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                placeholder="••••••••"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mc-form-input"
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                className="mc-password-toggle"
                aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
              >
                <i className={`ti ${showPassword ? 'ti-eye-off' : 'ti-eye'}`} />
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mc-btn-primary mc-btn-primary--block"
          >
            {loading ? 'Connexion…' : 'Se connecter'}
          </button>

          <p style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.85rem' }}>
            <a href="/mot-de-passe-oublie/" style={{ color: 'var(--mc-accent)', textDecoration: 'none' }}>
              Mot de passe oublié ?
            </a>
          </p>
          {!adminLogin && (
            <p className="mc-auth-footer">
              Pas encore de compte ?{' '}
              <Link to={`/inscription/${location.search}`}>
                S'inscrire
              </Link>
            </p>
          )}
            </form>
          </div>
        </div>
      </section>
    </div>
  );
}
