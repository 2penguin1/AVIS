import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: Vite serves the SPA on :5173 and proxies API + image routes to FastAPI on :8000,
// so the api client can use root-relative paths that also work in production (same origin).
const api = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/images': api,
      '/violations': api,
      '/review-queue': api,
      '/analytics': api,
      '/runtime': api,
      '/files': api,
    },
  },
  build: { outDir: 'dist', emptyOutDir: true },
})
