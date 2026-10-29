import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// GitHub Pages serves the repo at /second-serve/; Vercel builds with VITE_BASE=/.
const base = process.env.VITE_BASE ?? '/second-serve/'

export default defineConfig({
  base,
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  // Why: /sources renders ../docs/sources.json directly so the page can never drift from the research doc.
  server: { fs: { allow: ['..'] } },
})
