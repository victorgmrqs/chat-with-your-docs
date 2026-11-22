import { describe, expect, it } from 'vitest'

import {
  answeredResponse,
  documentResponse,
  insufficientResponse,
  MESSAGES,
  passageResponse,
  sourceResponse,
} from '@/mocks/data'

import { toTurnOutcome } from './chat'

describe('toTurnOutcome', () => {
  const handbook = documentResponse({ filename: 'Employee_Handbook_2026.pdf' })

  it('maps an answer and its sources (file, page or heading, passage)', () => {
    const source = sourceResponse(handbook, 1, { page: null, heading: 'Leave > Vacation', passage: '20 days.' })

    expect(toTurnOutcome(answeredResponse([source], 'Twenty days [1].'))).toEqual({
      status: 'answered',
      answer: 'Twenty days [1].',
      sources: [
        {
          number: 1,
          chunkId: source.chunk_id,
          documentId: handbook.id,
          filename: 'Employee_Handbook_2026.pdf',
          page: null,
          heading: 'Leave > Vacation',
          passage: '20 days.',
        },
      ],
    })
  })

  it('maps insufficient evidence to the backend message and an unnumbered passage (DOM-10)', () => {
    const outcome = toTurnOutcome(insufficientResponse(passageResponse(handbook, { passage: 'Parking.' })))

    expect(outcome).toMatchObject({ status: 'insufficient', message: MESSAGES.insufficientEvidence })
    expect(outcome.status === 'insufficient' && outcome.relatedPassage).not.toHaveProperty('number')
  })

  it('keeps a missing related passage as null', () => {
    expect(toTurnOutcome(insufficientResponse())).toMatchObject({ relatedPassage: null })
  })
})
