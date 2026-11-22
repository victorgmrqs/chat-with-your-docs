import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach } from 'vitest'

import { mockDb } from '@/mocks/db'
import { server } from '@/mocks/server'

// findBy*/waitFor wait for MSW responses and renders: 1 s (the default) flakes on a loaded machine.
configure({ asyncUtilTimeout: 5000 })

// Any request without a handler fails the test: the API is never reached for real. Listening
// at import time patches fetch before test files import the API client.
server.listen({ onUnhandledFrame: 'error' })
afterEach(() => {
  cleanup()
  server.resetHandlers()
  mockDb.reset()
})
afterAll(() => server.close())
