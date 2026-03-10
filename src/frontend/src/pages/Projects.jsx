import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FolderPlus, FolderOpen, Loader2, Pencil, Trash2, LayoutGrid } from 'lucide-react'

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

function updateProjectApi(apiBase, projectId, body) {
  return fetch(`${apiBase}/api/projects/${projectId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async (r) => {
    const data = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(data.detail || r.statusText)
    return data
  })
}

function deleteProjectApi(apiBase, projectId) {
  return fetch(`${apiBase}/api/projects/${projectId}`, { method: 'DELETE' }).then(async (r) => {
    const data = await r.json().catch(() => ({}))
    if (!r.ok) throw new Error(data.detail || r.statusText)
    return data
  })
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { dateStyle: 'medium' })
  } catch {
    return '—'
  }
}

export default function Projects({ apiBase }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
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

  const updateMutation = useMutation({
    mutationFn: ({ projectId, body }) => updateProjectApi(apiBase, projectId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', apiBase] })
      setEditingId(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (projectId) => deleteProjectApi(apiBase, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', apiBase] })
    },
  })

  function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) return
    createMutation.mutate({ name: name.trim(), description: description.trim() || null })
  }

  function startEdit(p) {
    setEditingId(p.id)
    setEditName(p.name)
    setEditDescription(p.description || '')
  }

  function handleUpdate(e, projectId) {
    e.preventDefault()
    updateMutation.mutate({ projectId, body: { name: editName.trim() || undefined, description: editDescription.trim() || null } })
  }

  function handleDelete(projectId, e) {
    e.preventDefault()
    e.stopPropagation()
    if (!window.confirm('Delete this project? Pipeline runs will be unlinked.')) return
    deleteMutation.mutate(projectId)
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
        <div className="mt-8 rounded-xl border-2 border-dashed border-slate-600 bg-slate-800/30 py-16 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-700/80">
            <LayoutGrid className="h-8 w-8 text-slate-500" aria-hidden />
          </div>
          <p className="mb-2 text-slate-400">No projects yet.</p>
          <p className="mb-6 text-sm text-slate-500">Create one to scope pipeline runs and MLflow experiments.</p>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
          >
            <FolderPlus className="h-4 w-4" />
            Create your first project
          </button>
        </div>
      ) : (
        <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <li key={p.id} className="rounded-xl border border-slate-700 bg-slate-800/60 overflow-hidden">
              {editingId === p.id ? (
                <form onSubmit={(e) => handleUpdate(e, p.id)} className="p-4 space-y-3">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    placeholder="Project name"
                    className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100"
                    required
                  />
                  <input
                    type="text"
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    placeholder="Description (optional)"
                    className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100"
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={updateMutation.isPending}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-1.5 text-sm text-white hover:bg-sky-500 disabled:opacity-60"
                    >
                      {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(null)}
                      className="rounded-lg border border-slate-600 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700"
                    >
                      Cancel
                    </button>
                  </div>
                  {updateMutation.isError && <p className="text-sm text-red-400">{updateMutation.error.message}</p>}
                </form>
              ) : (
                <>
                  <Link
                    to={`/projects/${p.id}/workspace`}
                    className="block p-4 transition-colors hover:bg-slate-700/40"
                  >
                    <div className="flex items-start gap-3">
                      <FolderOpen className="h-5 w-5 shrink-0 text-sky-400" />
                      <div className="min-w-0 flex-1">
                        <span className="font-semibold text-slate-100">{p.name}</span>
                        {p.description && (
                          <p className="mt-0.5 text-sm text-slate-500 line-clamp-2">{p.description}</p>
                        )}
                        <div className="mt-2 flex flex-wrap gap-x-3 text-xs font-medium text-slate-400">
                          <span>Created {formatDate(p.created_at)}</span>
                          <span>{p.active_runs != null ? `${p.active_runs} active run${p.active_runs !== 1 ? 's' : ''}` : '—'}</span>
                        </div>
                      </div>
                      <span className="text-xs text-slate-500 shrink-0">Open workspace →</span>
                    </div>
                  </Link>
                  <div className="flex items-center justify-end gap-1 border-t border-slate-700 px-4 py-2">
                    <button
                      type="button"
                      onClick={() => startEdit(p)}
                      disabled={deleteMutation.isPending}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-600 bg-slate-700/50 p-1.5 text-slate-300 hover:bg-slate-600 hover:text-slate-100 disabled:opacity-60"
                      title="Edit"
                      aria-label="Edit project"
                    >
                      <Pencil className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={(e) => handleDelete(p.id, e)}
                      disabled={deleteMutation.isPending}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-600 bg-slate-700/50 p-1.5 text-red-400 hover:bg-red-900/30 hover:border-red-500/50 disabled:opacity-60"
                      title="Delete"
                      aria-label="Delete project"
                    >
                      {deleteMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                    </button>
                  </div>
                  {deleteMutation.isError && deleteMutation.variables === p.id && (
                    <p className="px-4 pb-2 text-sm text-red-400">{deleteMutation.error.message}</p>
                  )}
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
