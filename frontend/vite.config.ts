import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // En developpement le front tourne sur :5173 et l'API sur :8000.
    // Ce proxy permet au code d'appeler /api/... en relatif, exactement
    // comme en production ou les deux sont servis par le meme serveur.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
