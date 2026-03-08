import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import Form from '@rjsf/core'
import validator from '@rjsf/validator-ajv8'
import { Loader2 } from 'lucide-react'

function fetchSchema(apiBase, name) {
  return fetch(`${apiBase}/api/schemas/${name}`).then((r) => {
    if (!r.ok) throw new Error(r.statusText)
    return r.json()
  })
}

const schemaNames = [
  { id: 'pipeline', label: 'Pipeline config' },
  { id: 'thermal', label: 'Thermal config' },
]

export default function ConfigForm({ apiBase }) {
  const [schemaId, setSchemaId] = useState('pipeline')
  const [formData, setFormData] = useState({})
  const [submitStatus, setSubmitStatus] = useState(null)

  const { data: schema, isLoading } = useQuery({
    queryKey: ['schema', apiBase, schemaId],
    queryFn: () => fetchSchema(apiBase, schemaId),
    staleTime: 60_000,
  })

  const uiSchema = useMemo(() => ({
    'ui:submitButtonOptions': { submitText: 'Save / Apply', norender: true },
  }), [])

  function handleSubmit({ formData: fd }) {
    setFormData(fd)
    setSubmitStatus('Config is client-side only; save to YAML or use as run parameters in Run Pipeline.')
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading schema…
      </div>
    )
  }

  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">Config forms</h1>
      <p className="mt-1 text-sm text-slate-500">
        Forms generated from Pydantic models. Use these values when running the pipeline (or save to config YAML).
      </p>

      <div className="mt-4">
        <label htmlFor="schema-select" className="block text-sm font-medium text-slate-300">Schema</label>
        <select
          id="schema-select"
          value={schemaId}
          onChange={(e) => setSchemaId(e.target.value)}
          className="mt-1 rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-slate-100"
        >
          {schemaNames.map((s) => (
            <option key={s.id} value={s.id}>{s.label}</option>
          ))}
        </select>
      </div>

      {schema && (
        <div className="mt-6 rounded-xl border border-slate-700 bg-slate-800/60 p-4">
          <Form
            schema={schema}
            formData={formData}
            validator={validator}
            uiSchema={uiSchema}
            onChange={(e) => setFormData(e.formData)}
            onSubmit={handleSubmit}
            templates={{
              ButtonTemplates: {
                SubmitButton: (props) => (
                  <button
                    type="submit"
                    className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
                    {...props}
                  >
                    {props.label || 'Submit'}
                  </button>
                ),
              },
            }}
          />
          <style>{`
            .rjsf .form-group label { color: rgb(203 213 225); }
            .rjsf input, .rjsf select { background: rgb(30 41 59); border-color: rgb(71 85 105); color: rgb(241 245 249); }
            .rjsf .form-control { border-radius: 0.5rem; }
          `}</style>
        </div>
      )}

      {submitStatus && (
        <p className="mt-4 text-sm text-slate-400">{submitStatus}</p>
      )}
    </>
  )
}
