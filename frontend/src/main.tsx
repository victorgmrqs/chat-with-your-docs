import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

/** `VITE_API_MOCKS=true npm run dev` serves the API from MSW (src/mocks): no backend needed. */
async function enableMocking() {
  if (!import.meta.env.DEV || import.meta.env.VITE_API_MOCKS !== 'true') return
  const { worker } = await import('./mocks/browser')
  await worker.start({ onUnhandledFrame: 'bypass' })
}

void enableMocking().then(() =>
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  ),
)
