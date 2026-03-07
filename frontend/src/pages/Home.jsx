import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <>
      <h1>QASIC Engineering-as-Code</h1>
      <p>Run protocols, routing, pipeline, and inverse design from the menu below.</p>
      <section className="card">
        <h2>Actions</h2>
        <p><Link to="/run/protocol">Run protocol</Link> — Teleport, Bell, commitment, or thief (sim or IBM hardware)</p>
        <p><Link to="/run/routing">Run routing</Link> — QUBO/QAOA logical→physical mapping (sim or IBM, optional fast)</p>
        <p><Link to="/run/pipeline">Run full pipeline</Link> — Routing then inverse design</p>
        <p><Link to="/run/inverse">Inverse design</Link> — Topology → phase profile (optional phase band π)</p>
        <p><Link to="/results">View last results</Link> — Routing mapping and phase stats</p>
        <p><Link to="/docs">Docs</Link> — Architecture, QUANTUM_ASIC, whitepapers</p>
      </section>
    </>
  )
}
