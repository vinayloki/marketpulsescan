import { Link } from 'react-router-dom'
import { Home } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center animate-slide-up">
      <div className="text-6xl font-bold text-gradient mb-4">404</div>
      <p className="text-[var(--color-text-secondary)] text-lg mb-6">
        Page not found
      </p>
      <Link
        to="/"
        className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-md)] bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-500)] text-white text-sm font-medium transition-colors"
      >
        <Home className="h-4 w-4" />
        Back to Dashboard
      </Link>
    </div>
  )
}
