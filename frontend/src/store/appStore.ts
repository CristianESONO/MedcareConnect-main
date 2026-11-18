import { create } from 'zustand';

type Theme = 'light' | 'dark';

interface AppState {
  theme: Theme;
  cartOpen: boolean;
  toggleTheme: () => void;
  toggleCart:  () => void;
}

function applyTheme(t: Theme) {
  document.documentElement.classList.toggle('dark', t === 'dark');
  localStorage.setItem('mc_theme', t);
}

export const useAppStore = create<AppState>((set, get) => ({
  theme: (localStorage.getItem('mc_theme') as Theme) || 'light',
  cartOpen: false,

  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    applyTheme(next);
    set({ theme: next });
  },

  toggleCart: () => set((s) => ({ cartOpen: !s.cartOpen })),
}));

localStorage.removeItem('mc_lang');

// Apply saved theme on load
applyTheme((localStorage.getItem('mc_theme') as Theme) || 'light');
