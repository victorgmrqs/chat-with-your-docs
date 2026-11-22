import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusChip } from './StatusChip'

describe('StatusChip', () => {
  it.each([
    ['indexing', 'Indexing…', 'text-status-indexing-foreground'],
    ['ready', 'Ready', 'text-status-ready-foreground'],
    ['failed', 'Failed', 'text-status-failed-foreground'],
  ] as const)('status_chip_states: %s shows "%s" with its status color', (status, label, color) => {
    render(<StatusChip status={status} />)

    const chip = screen.getByText(label)
    expect(chip).toHaveAttribute('data-variant', status)
    expect(chip).toHaveClass(`bg-status-${status}`, color)
  })

  it('uses red only for Failed', () => {
    render(
      <>
        <StatusChip status="indexing" />
        <StatusChip status="ready" />
      </>,
    )

    for (const chip of [screen.getByText('Indexing…'), screen.getByText('Ready')]) {
      expect(chip.className).not.toMatch(/destructive|status-failed/)
    }
  })
})
