import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from '@/App'

function renderWithProviders(initialRoute = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App', () => {
  it('renders the dashboard page by default', () => {
    renderWithProviders('/')
    expect(screen.getByText('Market Overview')).toBeInTheDocument()
  })

  it('renders the scanner page', () => {
    renderWithProviders('/scanner')
    // Use heading role to target the page title, not the nav label
    expect(screen.getByRole('heading', { name: 'Scanner' })).toBeInTheDocument()
  })

  it('renders the AI picks page', () => {
    renderWithProviders('/ai-picks')
    expect(screen.getByRole('heading', { name: 'AI Picks' })).toBeInTheDocument()
  })

  it('renders the sectors page', () => {
    renderWithProviders('/sectors')
    expect(screen.getByRole('heading', { name: 'Sectors' })).toBeInTheDocument()
  })

  it('renders 404 for unknown routes', () => {
    renderWithProviders('/unknown-route')
    expect(screen.getByText('404')).toBeInTheDocument()
  })

  it('shows the MarketPulse brand in header', () => {
    renderWithProviders('/')
    expect(screen.getByText('MarketPulse')).toBeInTheDocument()
  })
})
