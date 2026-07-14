import { Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { DashboardPage } from '@/pages/DashboardPage'
import { ScannerPage } from '@/pages/ScannerPage'
import { StockDetailPage } from '@/pages/StockDetailPage'
import { AiPicksPage } from '@/pages/AiPicksPage'
import { SectorsPage } from '@/pages/SectorsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="scanner" element={<ScannerPage />} />
        <Route path="stock/:symbol" element={<StockDetailPage />} />
        <Route path="ai-picks" element={<AiPicksPage />} />
        <Route path="sectors" element={<SectorsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
