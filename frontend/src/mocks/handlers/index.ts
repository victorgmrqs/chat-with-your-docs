import { chatHandlers } from './chat'
import { documentHandlers } from './documents'

export const handlers = [...documentHandlers, ...chatHandlers]
