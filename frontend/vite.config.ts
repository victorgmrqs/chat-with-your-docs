import { fileURLToPath } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { msw } from 'msw/vite'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  // msw: serves the mock worker script for VITE_API_MOCKS=true (src/main.tsx). Dev server only,
  // so builds and the image never ship mockServiceWorker.js.
  plugins: [react(), tailwindcss(), { ...msw({ mode: 'worker-only' }), apply: 'serve' }],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api/': {
        // Same variable as the nginx image; e.g. http://host.docker.internal:8000 to reach the
        // Compose backend from the dev container.
        target: process.env.BACKEND_URL ?? 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.node-globals.ts', './src/test/setup.ts'],
    // Screen-level tests chain several MSW round trips and renders; a loaded machine can take
    // longer than the 5 s default.
    testTimeout: 15_000,
  },
})