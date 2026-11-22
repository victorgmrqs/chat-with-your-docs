import { useCallback, useRef, useState } from 'react'

import { api, ApiError, errorMessage, unwrap } from '@/api/client'
import { toTurnOutcome, type ChatTurn } from '@/lib/chat'

/**
 * The conversation. A failed question stays in the thread with the backend's message (DOM-18);
 * Retry sends the same question again in place, only for transient failures.
 */
export function useChat() {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  // Not crypto.randomUUID(): it only exists in a secure context (HTTPS or localhost).
  const turnCount = useRef(0)

  const replaceTurn = useCallback((next: ChatTurn) => {
    setTurns((current) => current.map((turn) => (turn.id === next.id ? next : turn)))
  }, [])

  const send = useCallback(async (id: string, question: string) => {
    let next: ChatTurn
    try {
      const response = await unwrap(api.POST('/chat', { body: { question } }))
      next = { id, question, ...toTurnOutcome(response) }
    } catch (error) {
      // Anything that is not an API answer (a bug, an aborted request) is worth one more try.
      const retryable = error instanceof ApiError ? error.transient : true
      next = { id, question, status: 'error', message: errorMessage(error), retryable }
    }
    replaceTurn(next)
  }, [replaceTurn])

  const ask = useCallback(
    (question: string) => {
      turnCount.current += 1
      const id = `turn-${turnCount.current}`
      setTurns((current) => [...current, { id, question, status: 'loading' }])
      void send(id, question)
    },
    [send],
  )

  const retry = useCallback(
    (turn: ChatTurn) => {
      replaceTurn({ id: turn.id, question: turn.question, status: 'loading' })
      void send(turn.id, turn.question)
    },
    [replaceTurn, send],
  )

  // DOM-17: one answer at a time.
  const isLoading = turns.some((turn) => turn.status === 'loading')

  return { turns, isLoading, ask, retry }
}
