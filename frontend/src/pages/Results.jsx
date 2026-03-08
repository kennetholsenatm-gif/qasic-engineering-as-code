import { useQuery } from '@tanstack/react-query'

function fetchLatest(apiBase) {
  return fetch(`${apiBase}/api/results/latest`).then(async (r) => {
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
    return r.json()
  })
}

export default function Results({ apiBase }) {
  const { data, error, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['results', 'latest', apiBase],
    queryFn: () => fetchLatest(apiBase),
    staleTime: 15_000,
    refetchInterval: 30_000,
  })

  if (error) return <p className="error">{error.message}</p>
  if (isLoading) return <p>Loading…</p>

  return (
    <>
      <h1 className="text-xl font-semibold">Last results</h1>
      {isRefetching && <p className="muted text-sm">Refreshing…</p>}
      <button type="button" onClick={() => refetch()} className="mb-4 rounded bg-slate-600 px-3 py-1 text-sm hover:bg-slate-500">
        Refresh
      </button>
      {!data?.routing && !data?.inverse && (
        <p>No results yet. Run pipeline or routing + inverse first.</p>
      )}
      {data?.routing && (
        <section className="card">
          <h2>Routing</h2>
          <pre>{JSON.stringify(data.routing, null, 2)}</pre>
        </section>
      )}
      {data?.inverse && (
        <section className="card">
          <h2>Inverse design</h2>
          <pre>{JSON.stringify(data.inverse, null, 2)}</pre>
        </section>
      )}
    </>
  )
}
