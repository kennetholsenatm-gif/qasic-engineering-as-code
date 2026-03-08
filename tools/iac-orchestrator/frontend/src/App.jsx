import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Pipelines from './pages/Pipelines'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Pipelines apiBase={API_BASE} />} />
        <Route path="*" element={<Pipelines apiBase={API_BASE} />} />
      </Routes>
    </BrowserRouter>
  )
}
