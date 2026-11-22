import { useCallback, useRef, useState } from 'react'

import { api, errorMessage, unwrap, type DocumentResponse } from '@/api/client'
import type { UploadRejection } from '@/components/DocumentSidebar'

/**
 * Uploads files one request each. A rejection (DOM-01) or failed request is shown with the
 * backend's message (DOM-16). Files are kept by document id for this session, so a document that
 * failed with indexing_failed can be sent again without picking it (DOM-04).
 */
export function useUpload(onUploaded: (document: DocumentResponse) => void) {
  const [rejection, setRejection] = useState<UploadRejection | null>(null)
  const files = useRef(new Map<string, File>())

  const uploadOne = useCallback(
    async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      try {
        const document = await unwrap(
          api.POST('/documents', {
            // openapi-typescript types the binary field as a string; the real body is the form.
            body: { file: '' },
            bodySerializer: () => form,
          }),
        )
        files.current.set(document.id, file)
        onUploaded(document)
      } catch (error) {
        setRejection({ filename: file.name, message: errorMessage(error) })
      }
    },
    [onUploaded],
  )

  const upload = useCallback(
    async (selected: Iterable<File>) => {
      setRejection(null)
      await Promise.all(Array.from(selected, uploadOne))
    },
    [uploadOne],
  )

  /** The file uploaded this session for a document, if any (lost on reload). */
  const fileFor = useCallback((documentId: string) => files.current.get(documentId), [])

  return { upload, rejection, fileFor }
}
