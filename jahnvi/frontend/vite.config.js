// TODO: Jahnvi — configure Vite for React.
// Add proxy for local backend: /api → http://localhost:8000
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
