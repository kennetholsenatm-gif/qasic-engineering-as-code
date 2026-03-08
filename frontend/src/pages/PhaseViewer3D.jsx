import { useState, useEffect, useRef } from 'react'

export default function PhaseViewer3D({ apiBase }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const containerRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${apiBase}/api/results/inverse-phases`)
      .then(r => {
        if (!r.ok) throw new Error(r.statusText || 'No phase data')
        return r.json()
      })
      .then(d => { if (!cancelled) setData(d) })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [apiBase])

  useEffect(() => {
    if (!data || !data.grid_2d || !containerRef.current) return
    import('plotly.js-dist-min')
      .then(module => {
        const Plotly = module.default || module
        const grid = data.grid_2d
        const z = Array.isArray(grid[0]) ? grid : [grid]
        const layout = {
          title: 'Phase profile (inverse design)',
          margin: { t: 40, r: 20, b: 40, l: 20 },
          scene: {
            xaxis: { title: 'x' },
            yaxis: { title: 'y' },
            zaxis: { title: 'phase (rad)' },
            aspectmode: 'data',
          },
        }
        const trace = { z, type: 'surface', colorscale: 'Viridis' }
        Plotly.newPlot(containerRef.current, [trace], layout, { responsive: true })
      })
      .catch(() => setError('Plotly failed to load'))
  }, [data])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p>Loading phase data…</p>

  return (
    <>
      <h1>Phase profile (3D)</h1>
      <p>Inverse design phase array as a surface (grid shape: {data.grid_shape?.join(' × ') || '—'}).</p>
      <div ref={containerRef} style={{ width: '100%', minHeight: '400px' }} />
    </>
  )
}
