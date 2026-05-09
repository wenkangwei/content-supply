import { Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from './components/layout/MainLayout'
import { Dashboard } from './pages/Dashboard'
import { Items } from './pages/Items'
import { ItemDetail } from './pages/ItemDetail'
import { Feeds } from './pages/Feeds'
import { Crawl } from './pages/Crawl'
import { Hot } from './pages/Hot'
import { Rewrite } from './pages/Rewrite'
import { Cleanup } from './pages/Cleanup'
import { Settings } from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/items" element={<Items />} />
        <Route path="/items/:id" element={<ItemDetail />} />
        <Route path="/feeds" element={<Feeds />} />
        <Route path="/crawl" element={<Crawl />} />
        <Route path="/hot" element={<Hot />} />
        <Route path="/rewrite" element={<Rewrite />} />
        <Route path="/cleanup" element={<Cleanup />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
