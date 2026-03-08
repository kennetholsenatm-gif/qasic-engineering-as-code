import { useState, useEffect } from 'react'

export default function Docs({ apiBase }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch(`${apiBase}/api/docs/links`)
      .then(r => r.json())
      .then(d => { if (!cancelled) setData(d) })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [apiBase])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p>Loading…</p>

  return (
    <>
      <h1>Documentation</h1>
      <ul>
        {data.links?.map((link, i) => (
          <li key={i}>
            {link.exists && link.url ? (
              <a href={link.url} target="_blank" rel="noopener noreferrer">{link.name}</a>
            ) : (
              <span>{link.name}</span>
            )}
            {' — '}
            <code>{link.path}</code>
            {link.exists && ' (exists)'}
          </li>
        ))}
      </ul>
      <p>Open links above to view markdown in the browser, or read <code>docs/</code> and <code>engineering/README.md</code> in the repo.</p>
    </>
  )
}
