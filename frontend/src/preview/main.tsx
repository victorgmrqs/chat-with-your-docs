// Dev-only design preview: /preview.html#<screen>. Never imported by the app entry point.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import '../index.css'
import { Preview } from './Preview'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Preview />
  </StrictMode>,
)
