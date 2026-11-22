// Static data for the design preview, copied from the handoff screens. Failure and rejection
// copy is the backend's own (DOM-01, DOM-03, DOM-16), not the PDF-only copy of the PNGs.
import type { ChatTurn, Passage, Source } from '@/lib/chat'
import type { DocumentItem } from '@/lib/documents'

const ready = (id: string, filename: string): DocumentItem => ({ id, filename, status: 'ready' })
const indexing = (id: string, filename: string): DocumentItem => ({ id, filename, status: 'indexing' })

export const NO_TEXT_MESSAGE =
  'No selectable text was found (for example a scanned PDF). Upload another version with selectable text.'
export const INDEXING_FAILED_MESSAGE =
  'Indexing failed for a temporary reason. Upload the same file again to retry.'
export const INSUFFICIENT_MESSAGE =
  'I couldn’t find enough evidence in the indexed documents to answer this question.'

export const scannedFailure: DocumentItem = {
  id: 'floorplan',
  filename: 'Office_Floorplan_Scan.pdf',
  status: 'failed',
  failureMessage: NO_TEXT_MESSAGE,
  canRetry: false,
}

export const transientFailure: DocumentItem = {
  id: 'benefits-failed',
  filename: 'Benefits_Overview_2026.pdf',
  status: 'failed',
  failureMessage: INDEXING_FAILED_MESSAGE,
  canRetry: true,
}

export const indexingDocuments: DocumentItem[] = [
  ready('handbook', 'Employee_Handbook_2026.pdf'),
  ready('remote', 'Remote_Work_Policy.pdf'),
  indexing('travel', 'Travel_Expense_Policy.pdf'),
  indexing('benefits', 'Benefits_Overview_2026.pdf'),
  indexing('security', 'IT_Security_Guidelines.pdf'),
  scannedFailure,
]

export const readyDocuments: DocumentItem[] = [
  ready('handbook', 'Employee_Handbook_2026.pdf'),
  ready('remote', 'Remote_Work_Policy.pdf'),
  ready('travel', 'Travel_Expense_Policy.pdf'),
  ready('benefits', 'Benefits_Overview_2026.pdf'),
  ready('security', 'IT_Security_Guidelines.pdf'),
]

export const coworkingSources: Source[] = [
  {
    number: 1,
    chunkId: 'remote-4',
    documentId: 'remote',
    filename: 'Remote_Work_Policy.pdf',
    page: 4,
    heading: null,
    passage:
      'Employees on a fully remote arrangement may work from a coworking space, provided the arrangement is approved by their manager before the first booking. Approval is recorded in the HR portal and renewed every twelve months together with the remote work agreement.',
  },
  {
    number: 2,
    chunkId: 'travel-6',
    documentId: 'travel',
    filename: 'Travel_Expense_Policy.pdf',
    page: 6,
    heading: null,
    passage: 'Coworking memberships are reimbursable up to $250 per calendar month.',
  },
]

export const coworkingQuestion =
  "Can I expense a coworking space while working remotely? What's the monthly limit?"
export const coworkingAnswer =
  'Yes. Fully remote employees may use a coworking space if their manager approves it before the first booking [1]. Coworking memberships are reimbursed up to $250 per calendar month [2].'

export const relatedPassage: Passage = {
  chunkId: 'handbook-31',
  documentId: 'handbook',
  filename: 'Employee_Handbook_2026.pdf',
  page: 31,
  heading: null,
  passage:
    'Full-time employees are eligible for 16 weeks of paid parental leave after six months of continuous service.',
}

export const loadingTurn: ChatTurn = {
  id: 'equipment',
  question: 'What equipment does the company provide for remote employees?',
  status: 'loading',
}

export const answeredTurn: ChatTurn = {
  id: 'coworking',
  question: coworkingQuestion,
  status: 'answered',
  answer: coworkingAnswer,
  sources: coworkingSources,
}

export const insufficientTurn: ChatTurn = {
  id: 'parental',
  question: 'What is the parental leave policy for contractors?',
  status: 'insufficient',
  message: INSUFFICIENT_MESSAGE,
  relatedPassage,
}

export const ERROR_MESSAGE = 'The request timed out. Your question was kept, so you can try again.'
