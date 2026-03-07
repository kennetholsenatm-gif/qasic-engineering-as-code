import { useState, useEffect } from 'react'

export default function Results({ apiBase }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${apiBase}/api/results/latest`)
      .then(r => {
        if (!r.ok) throw new Error(r.statusText || 'Request failed')
        return r.json()
      })
      .then(d => { if (!cancelled) setData(d) })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [apiBase])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p>Loading…</p>

  return (
    <>
      <h1>Last results</h1>
      {!data.routing && !data.inverse && (
        <p>No results yet. Run pipeline or routing + inverse first.</p>
      )}
      {data.routing && (
        <section className="card">
          <h2>Routing</h2>
          <pre>{JSON.stringify(data.routing, null, 2)}</pre>
        </section>
      )}
      {data.inverse && (
        <section className="card">
          <h2>Inverse design</h2>
          <pre>{JSON.stringify(data.inverse, null, 2)}</pre>
        </section>
      )}
    </>
  )
}
