import { BrowserRouter, Routes, Route, useSearchParams } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import RunProtocol from './pages/RunProtocol'
import RunRouting from './pages/RunRouting'
import RunPipeline from './pages/RunPipeline'
import RunInverse from './pages/RunInverse'
import RunQuantumIllumination from './pages/RunQuantumIllumination'
import RunQuantumRadar from './pages/RunQuantumRadar'
import RunQKD from './pages/RunQKD'
import RunTeleportation from './pages/RunTeleportation'
import RunCommitment from './pages/RunCommitment'
import AppBQTC from './pages/AppBQTC'
import AppQRNC from './pages/AppQRNC'
import EngineeringThermal from './pages/EngineeringThermal'
import EngineeringHEaC from './pages/EngineeringHEaC'
import Results from './pages/Results'
import Docs from './pages/Docs'
import PhaseViewer3D from './pages/PhaseViewer3D'
import Applications from './pages/Applications'
import Projects from './pages/Projects'
import ConfigForm from './pages/ConfigForm'
import Workflows from './pages/Workflows'
import Deploy from './pages/Deploy'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

function ResultsWithProject() {
  const [searchParams] = useSearchParams()
  const projectId = searchParams.get('project_id')
  return <Results apiBase={API_BASE} projectId={projectId ? Number(projectId) : null} />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="projects" element={<Projects apiBase={API_BASE} />} />
          <Route path="run/protocol" element={<RunProtocol apiBase={API_BASE} />} />
          <Route path="run/routing" element={<RunRouting apiBase={API_BASE} />} />
          <Route path="run/quantum-illumination" element={<RunQuantumIllumination apiBase={API_BASE} />} />
          <Route path="run/quantum-radar" element={<RunQuantumRadar apiBase={API_BASE} />} />
          <Route path="run/pipeline" element={<RunPipeline apiBase={API_BASE} />} />
          <Route path="run/inverse" element={<RunInverse apiBase={API_BASE} />} />
          <Route path="run/qkd" element={<RunQKD apiBase={API_BASE} />} />
          <Route path="run/teleportation" element={<RunTeleportation apiBase={API_BASE} />} />
          <Route path="run/commitment" element={<RunCommitment apiBase={API_BASE} />} />
          <Route path="results" element={<ResultsWithProject />} />
          <Route path="phase-viewer" element={<PhaseViewer3D apiBase={API_BASE} />} />
          <Route path="engineering/thermal" element={<EngineeringThermal apiBase={API_BASE} />} />
          <Route path="engineering/heac" element={<EngineeringHEaC apiBase={API_BASE} />} />
          <Route path="apps/bqtc" element={<AppBQTC apiBase={API_BASE} />} />
          <Route path="apps/qrnc" element={<AppQRNC apiBase={API_BASE} />} />
          <Route path="config" element={<ConfigForm apiBase={API_BASE} />} />
          <Route path="workflows" element={<Workflows apiBase={API_BASE} />} />
          <Route path="applications" element={<Applications apiBase={API_BASE} />} />
          <Route path="deploy" element={<Deploy apiBase={API_BASE} />} />
          <Route path="docs" element={<Docs apiBase={API_BASE} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
