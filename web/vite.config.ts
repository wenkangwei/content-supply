import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/feeds': { target: 'http://localhost:8010', changeOrigin: true },
      '/items': { target: 'http://localhost:8010', changeOrigin: true },
      '/crawl': { target: 'http://localhost:8010', changeOrigin: true },
      '/hot': { target: 'http://localhost:8010', changeOrigin: true },
      '/rewrite': { target: 'http://localhost:8010', changeOrigin: true },
      '/cleanup': { target: 'http://localhost:8010', changeOrigin: true },
      '/tags': { target: 'http://localhost:8010', changeOrigin: true },
      '/api': { target: 'http://localhost:8010', changeOrigin: true },
      '/docs': { target: 'http://localhost:8010', changeOrigin: true },
      '/redoc': { target: 'http://localhost:8010', changeOrigin: true },
      '/openapi.json': { target: 'http://localhost:8010', changeOrigin: true },
    },
  },
})
