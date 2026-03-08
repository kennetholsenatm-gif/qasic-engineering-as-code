import { Link } from 'react-router-dom'
import {
  Play,
  Route,
  Sparkles,
  FileBarChart,
  BookOpen,
  Box,
  Radio,
  Satellite,
  FlaskConical,
} from 'lucide-react'

const actions = [
  {
    to: '/run/protocol',
    title: 'Run protocol',
    description: 'Teleport, Bell, commitment, or thief (sim or IBM hardware).',
    icon: Radio,
  },
  {
    to: '/run/routing',
    title: 'Run routing',
    description: 'QUBO/QAOA logical→physical mapping (sim or IBM, optional fast).',
    icon: Route,
  },
  {
    to: '/run/pipeline',
    title: 'Run full pipeline',
    description: 'Routing then inverse design in one run.',
    icon: Play,
  },
  {
    to: '/run/inverse',
    title: 'Inverse design',
    description: 'Topology → phase profile (optional phase band π).',
    icon: Sparkles,
  },
  {
    to: '/results',
    title: 'View last results',
    description: 'Routing mapping and phase stats from the latest run.',
    icon: FileBarChart,
  },
  {
    to: '/phase-viewer',
    title: 'Phase viewer (3D)',
    description: 'Inverse design phase array as an interactive 3D surface.',
    icon: Box,
  },
  {
    to: '/docs',
    title: 'Docs',
    description: 'Architecture, QUANTUM_ASIC, whitepapers.',
    icon: BookOpen,
  },
  {
    to: '/applications',
    title: 'Applications',
    description: 'QRNC, BQTC, and other apps.',
    icon: FlaskConical,
  },
]

export default function Home() {
  return (
    <>
      <h1 className="text-2xl font-semibold text-slate-100">QASIC Engineering-as-Code</h1>
      <p className="mt-1 text-slate-400">
        Run protocols, routing, pipeline, and inverse design from the cards below.
      </p>
      <section className="mt-8">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">
          Actions
        </h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {actions.map(({ to, title, description, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="group flex flex-col rounded-xl border border-slate-700/60 bg-slate-800/60 p-4 transition-colors hover:border-sky-500/40 hover:bg-slate-800"
            >
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 transition-colors group-hover:bg-sky-500/30">
                <Icon className="h-5 w-5" aria-hidden />
              </div>
              <h3 className="font-medium text-slate-100">{title}</h3>
              <p className="mt-1 text-sm text-slate-500">{description}</p>
            </Link>
          ))}
        </div>
      </section>
    </>
  )
}
