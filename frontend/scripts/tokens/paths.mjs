// Paths shared by the token scripts, resolved from this file (not from the working directory).
import { fileURLToPath } from 'node:url'

export const repoRoot = fileURLToPath(new URL('../../../', import.meta.url))
export const frontendRoot = fileURLToPath(new URL('../../', import.meta.url))
export const tokensFile = fileURLToPath(new URL('../../../docs/design-tokens.json', import.meta.url))
export const themeFile = fileURLToPath(new URL('../../src/styles/theme.css', import.meta.url))
export const cnFile = fileURLToPath(new URL('../../src/lib/utils.ts', import.meta.url))
