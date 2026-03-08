import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
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
      <nav>
        <Link to="/">Home</Link>
        <Link to="/run/protocol">Run protocol</Link>
        <Link to="/run/routing">Run routing</Link>
        <Link to="/run/quantum-illumination">Quantum illumination</Link>
        <Link to="/run/quantum-radar">Quantum radar</Link>
        <Link to="/run/pipeline">Run pipeline</Link>
        <Link to="/run/inverse">Inverse design</Link>
        <Link to="/results">Results</Link>
        <Link to="/phase-viewer">Phase viewer (3D)</Link>
        <Link to="/applications">Applications</Link>
        <Link to="/docs">Docs</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/run/protocol" element={<RunProtocol apiBase={API_BASE} />} />
        <Route path="/run/routing" element={<RunRouting apiBase={API_BASE} />} />
        <Route path="/run/quantum-illumination" element={<RunQuantumIllumination apiBase={API_BASE} />} />
        <Route path="/run/quantum-radar" element={<RunQuantumRadar apiBase={API_BASE} />} />
        <Route path="/run/pipeline" element={<RunPipeline apiBase={API_BASE} />} />
        <Route path="/run/inverse" element={<RunInverse apiBase={API_BASE} />} />
        <Route path="/results" element={<Results apiBase={API_BASE} />} />
        <Route path="/phase-viewer" element={<PhaseViewer3D apiBase={API_BASE} />} />
        <Route path="/applications" element={<Applications apiBase={API_BASE} />} />
        <Route path="/docs" element={<Docs apiBase={API_BASE} />} />
      </Routes>
    </BrowserRouter>
  )
}
