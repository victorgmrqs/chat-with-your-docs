// MSW for `VITE_API_MOCKS=true npm run dev`: the app runs without the backend. The worker script
// is served by the msw/vite plugin (vite.config.ts); nothing is committed under public/.
import { setupWorker } from 'msw/browser'

import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
