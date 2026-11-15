import { create } from 'zustand';

type Theme = 'light' | 'dark';
type Lang  = 'fr' | 'en';

interface AppState {
  theme: Theme;
  lang:  Lang;
  cartOpen: boolean;
  toggleTheme: () => void;
  setLang:     (l: Lang) => void;
  toggleCart:  () => void;
}

function applyTheme(t: Theme) {
  document.documentElement.classList.toggle('dark', t === 'dark');
  localStorage.setItem('mc_theme', t);
}

export const useAppStore = create<AppState>((set, get) => ({
  theme: (localStorage.getItem('mc_theme') as Theme) || 'light',
  lang:  (localStorage.getItem('mc_lang')  as Lang)  || 'fr',
  cartOpen: false,

  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    applyTheme(next);
    set({ theme: next });
  },

  setLang: (lang) => {
    localStorage.setItem('mc_lang', lang);
    set({ lang });
  },

  toggleCart: () => set((s) => ({ cartOpen: !s.cartOpen })),
}));

// Apply saved theme on load
applyTheme((localStorage.getItem('mc_theme') as Theme) || 'light');
