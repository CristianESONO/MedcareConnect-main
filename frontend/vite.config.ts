import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/react/' : '/',
  build: {
    outDir: '../backend/static/react',
    emptyOutDir: true,
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/healthcare': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/cart': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/users': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/sante': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/rdv': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/messaging': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/dashboard/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/admin/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/notifications/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/mot-de-passe-oublie': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/confiance/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
}));
