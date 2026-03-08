import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderPlus, FolderOpen, Loader2 } from 'lucide-react'

function fetchProjects(apiBase) {
  return fetch(`${apiBase}/api/projects`).then(async (r) => {
    if (!r.ok) return { projects: [] }
    return r.json()
  })
}

function createProjectApi(apiBase, body) {
  return fetch(`${apiBase}/api/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async (r) => {
    const data = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(data.detail || r.statusText)
    return data
  })
}

export default function Projects({ apiBase }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [showForm, setShowForm] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['projects', apiBase],
    queryFn: () => fetchProjects(apiBase),
    staleTime: 30_000,
  })
  const projects = data?.projects || []

  const createMutation = useMutation({
    mutationFn: (body) => createProjectApi(apiBase, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', apiBase] })
      setName('')
      setDescription('')
      setShowForm(false)
    },
  })

  function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) return
    createMutation.mutate({ name: name.trim(), description: description.trim() || null })
  }

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">Projects</h1>
      <p className="mt-1 text-sm text-slate-500">
        Create a project to group pipeline runs and tie them to an MLflow experiment.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
        >
          <FolderPlus className="h-4 w-4" />
          New project
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mt-4 rounded-xl border border-slate-700 bg-slate-800/60 p-4 space-y-3">
          <div>
            <label htmlFor="project-name" className="block text-sm font-medium text-slate-300">Name</label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Quantum Radar Metasurface"
              className="mt-1 w-full max-w-md rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100"
              required
            />
          </div>
          <div>
            <label htmlFor="project-desc" className="block text-sm font-medium text-slate-300">Description</label>
            <input
              id="project-desc"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional"
              className="mt-1 w-full max-w-md rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createMutation.isPending || !name.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-3 py-2 text-sm text-white hover:bg-sky-500 disabled:opacity-60"
            >
              {createMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700"
            >
              Cancel
            </button>
          </div>
          {createMutation.isError && <p className="text-sm text-red-400">{createMutation.error.message}</p>}
        </form>
      )}

      {isLoading ? (
        <div className="mt-6 flex items-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading…
        </div>
      ) : projects.length === 0 ? (
        <div className="mt-8 rounded-xl border border-dashed border-slate-600 bg-slate-800/30 py-12 text-center text-slate-500">
          No projects yet. Create one to scope pipeline runs and MLflow experiments.
        </div>
      ) : (
        <ul className="mt-6 space-y-2">
          {projects.map((p) => (
            <li key={p.id}>
              <Link
                to={`/results?project_id=${p.id}`}
                className="flex items-center gap-3 rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 text-slate-200 transition-colors hover:bg-slate-700/40"
              >
                <FolderOpen className="h-5 w-5 text-sky-400" />
                <div className="min-w-0 flex-1">
                  <span className="font-medium">{p.name}</span>
                  {p.description && <span className="ml-2 text-slate-500 text-sm">{p.description}</span>}
                </div>
                <span className="text-xs text-slate-500">View results →</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
