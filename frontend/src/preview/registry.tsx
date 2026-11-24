import { citedDocuments } from '@/lib/chat'

import {
  answeredTurn,
  coworkingSources,
  indexingDocuments,
  insufficientTurn,
  loadingTurn,
  readyDocuments,
} from './fixtures'
import { ComponentStates, Screen } from './screens'

export const SCREENS = {
  'empty-collection': {
    title: '1 · Empty collection',
    render: () => <Screen documents={[]} turns={[]} />,
  },
  indexing: {
    title: '2 · Indexing',
    render: () => <Screen documents={indexingDocuments} turns={[loadingTurn]} isLoading />,
  },
  'answer-two-sources': {
    title: '3 · Answer with two sources',
    render: () => (
      <Screen
        documents={readyDocuments}
        turns={[answeredTurn]}
        citations={citedDocuments(coworkingSources)}
      />
    ),
  },
  'not-enough-evidence': {
    title: '4 · Not enough evidence',
    render: () => (
      <Screen documents={readyDocuments} turns={[answeredTurn, insufficientTurn]} citations={{}} />
    ),
  },
  'component-states': {
    title: '5 · Component states',
    render: () => <ComponentStates />,
  },
} as const
