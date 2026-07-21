import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const base = process.env.VITE_BASE
  ?? (process.env.VITE_ENV === 'staging'
    ? '/marketpulsescan/staging/'
    : process.env.VITE_ENV === 'production'
      ? '/marketpulsescan/v2/'
      : '/')

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  base,
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    open: true,
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('react-dom') || id.includes('react-router')) {
            return 'vendor'
          }
          if (id.includes('lightweight-charts')) {
            return 'charts'
          }
          if (id.includes('@tanstack') || id.includes('zustand')) {
            return 'state'
          }
        },
      },
    },
  },
})
