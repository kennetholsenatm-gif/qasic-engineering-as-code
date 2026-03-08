import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import RunProtocol from './pages/RunProtocol'
import RunRouting from './pages/RunRouting'
import RunPipeline from './pages/RunPipeline'
import RunInverse from './pages/RunInverse'
import RunQuantumIllumination from './pages/RunQuantumIllumination'
import RunQuantumRadar from './pages/RunQuantumRadar'
import Results from './pages/Results'
import Docs from './pages/Docs'
import PhaseViewer3D from './pages/PhaseViewer3D'
import Applications from './pages/Applications'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="run/protocol" element={<RunProtocol apiBase={API_BASE} />} />
          <Route path="run/routing" element={<RunRouting apiBase={API_BASE} />} />
          <Route path="run/quantum-illumination" element={<RunQuantumIllumination apiBase={API_BASE} />} />
          <Route path="run/quantum-radar" element={<RunQuantumRadar apiBase={API_BASE} />} />
          <Route path="run/pipeline" element={<RunPipeline apiBase={API_BASE} />} />
          <Route path="run/inverse" element={<RunInverse apiBase={API_BASE} />} />
          <Route path="results" element={<Results apiBase={API_BASE} />} />
          <Route path="phase-viewer" element={<PhaseViewer3D apiBase={API_BASE} />} />
          <Route path="applications" element={<Applications apiBase={API_BASE} />} />
          <Route path="docs" element={<Docs apiBase={API_BASE} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
