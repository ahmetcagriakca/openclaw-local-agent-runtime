import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfirmDialog } from '../components/ConfirmDialog'

describe('ConfirmDialog', () => {
  const defaultProps = {
    open: true,
    title: 'Delete Mission',
    message: 'Are you sure?',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  }

  test('renders nothing when closed', () => {
    const { container } = render(<ConfirmDialog {...defaultProps} open={false} />)
    expect(container.innerHTML).toBe('')
  })

  test('renders title and message when open', () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText('Delete Mission')).toBeTruthy()
    expect(screen.getByText('Are you sure?')).toBeTruthy()
  })

  test('calls onConfirm when confirm button clicked', () => {
    const onConfirm = vi.fn()
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />)
    fireEvent.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalledOnce()
  })

  test('calls onCancel when cancel button clicked', () => {
    const onCancel = vi.fn()
    render(<ConfirmDialog {...defaultProps} onCancel={onCancel} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledOnce()
  })

  test('uses custom button labels', () => {
    render(<ConfirmDialog {...defaultProps} confirmLabel="Yes, delete" cancelLabel="No, keep" />)
    expect(screen.getByText('Yes, delete')).toBeTruthy()
    expect(screen.getByText('No, keep')).toBeTruthy()
  })

  test('danger variant has red styling', () => {
    render(<ConfirmDialog {...defaultProps} variant="danger" />)
    const confirmBtn = screen.getByText('Confirm')
    expect(confirmBtn.className).toContain('bg-red-600')
  })

  test('buttons disabled when loading', () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />)
    const confirmBtn = screen.getByText('Confirm')
    const cancelBtn = screen.getByText('Cancel')
    expect(confirmBtn.hasAttribute('disabled')).toBe(true)
    expect(cancelBtn.hasAttribute('disabled')).toBe(true)
  })

  test('has aria attributes for accessibility', () => {
    render(<ConfirmDialog {...defaultProps} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog.getAttribute('aria-modal')).toBe('true')
  })
})
