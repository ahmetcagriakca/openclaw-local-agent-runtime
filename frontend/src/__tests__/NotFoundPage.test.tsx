import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { NotFoundPage } from '../pages/NotFoundPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <NotFoundPage />
    </MemoryRouter>,
  )
}

describe('NotFoundPage', () => {
  test('renders 404 text', () => {
    renderPage()
    expect(screen.getByText('404')).toBeTruthy()
  })

  test('renders page not found message', () => {
    renderPage()
    expect(screen.getByText('Page not found')).toBeTruthy()
  })

  test('renders link to missions page', () => {
    renderPage()
    const link = screen.getByText('Go to Missions')
    expect(link).toBeTruthy()
    expect(link.getAttribute('href')).toBe('/missions')
  })
})
