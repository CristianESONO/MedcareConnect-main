export async function getCsrfToken(): Promise<string> {
  const response = await fetch('/api/auth/csrf/', { credentials: 'include' });
  if (!response.ok) {
    throw new Error('Impossible de préparer la connexion sécurisée.');
  }

  const data = (await response.json()) as { csrfToken?: string };
  if (!data.csrfToken) {
    throw new Error('Le jeton de sécurité est manquant.');
  }
  return data.csrfToken;
}
