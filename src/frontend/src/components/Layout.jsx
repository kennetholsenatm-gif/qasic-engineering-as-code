import { useState } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Home,
  FileBarChart,
  Box,
  Play,
  Route,
  Sparkles,
  Radio,
  Satellite,
  FlaskConical,
  BookOpen,
  Menu,
  X,
  ChevronDown,
  FolderOpen,
  Settings,
  GitBranch,
  Server,
} from 'lucide-react'

const navGroups = [
  {
    label: 'Dashboards',
    icon: LayoutDashboard,
    items: [
      { to: '/', label: 'Home', icon: Home },
      { to: '/projects', label: 'Projects', icon: FolderOpen },
      { to: '/results', label: 'Results', icon: FileBarChart },
      { to: '/phase-viewer', label: 'Phase Viewer 3D', icon: Box },
    ],
  },
  {
    label: 'Run simulations',
    icon: Play,
    items: [
      { to: '/run/pipeline', label: 'Pipeline', icon: Route },
      { to: '/run/routing', label: 'Routing', icon: Route },
      { to: '/run/inverse', label: 'Inverse design', icon: Sparkles },
      { to: '/config', label: 'Config forms', icon: Settings },
      { to: '/workflows', label: 'Workflows (DAG)', icon: GitBranch },
    ],
  },
  {
    label: 'Protocols',
    icon: Radio,
    items: [
      { to: '/run/protocol', label: 'Run protocol', icon: Play },
      { to: '/run/quantum-radar', label: 'Quantum radar', icon: Satellite },
      { to: '/run/quantum-illumination', label: 'Quantum illumination', icon: Sparkles },
    ],
  },
  {
    label: 'Resources',
    icon: BookOpen,
    items: [
      { to: '/docs', label: 'Docs', icon: BookOpen },
      { to: '/applications', label: 'Applications', icon: FlaskConical },
      { to: '/deploy', label: 'Deploy', icon: Server },
    ],
  },
]

function NavLink({ to, label, icon: Icon, isActive }) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
        isActive
          ? 'bg-slate-600 text-sky-200 font-medium'
          : 'text-slate-300 hover:bg-slate-700/60 hover:text-slate-100'
      }`}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {label}
    </Link>
  )
}

function NavGroup({ group, location, isOpen, onToggle }) {
  const Icon = group.icon
  const hasActive = group.items.some((item) => location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to)))

  return (
    <div className="mb-1">
      <button
        type="button"
        onClick={onToggle}
        className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider transition-colors ${
          hasActive ? 'text-sky-300' : 'text-slate-500'
        } hover:bg-slate-700/40 hover:text-slate-300`}
        aria-expanded={isOpen}
      >
        <Icon className="h-4 w-4 shrink-0" />
        <span className="flex-1">{group.label}</span>
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? '' : '-rotate-90'}`} />
      </button>
      {isOpen && (
        <div className="ml-2 mt-0.5 space-y-0.5 border-l border-slate-600 pl-2">
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              label={item.label}
              icon={item.icon}
              isActive={location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to))}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [groupOpen, setGroupOpen] = useState({})

  const toggleGroup = (label) => {
    setGroupOpen((prev) => ({ ...prev, [label]: prev[label] === false }))
  }

  return (
    <div className="flex min-h-screen bg-slate-900 text-slate-100">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          aria-label="Close menu"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform border-r border-slate-700/60 bg-slate-800/95 shadow-xl transition-transform duration-200 ease-out lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-slate-700/60 px-4 lg:justify-center">
          <span className="font-semibold text-sky-200">QASIC</span>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded p-1.5 text-slate-400 hover:bg-slate-700 hover:text-white lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="overflow-y-auto p-3" aria-label="Main">
          {navGroups.map((group) => (
            <NavGroup
              key={group.label}
              group={group}
              location={location}
              isOpen={groupOpen[group.label] !== false}
              onToggle={() => toggleGroup(group.label)}
            />
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-30 flex h-14 items-center border-b border-slate-700/60 bg-slate-900/90 px-4 backdrop-blur-sm lg:px-8">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
            aria-label="Open menu"
          >
            <Menu className="h-6 w-6" />
          </button>
          <span className="ml-2 text-sm text-slate-500 lg:ml-0">
            Engineering-as-Code
          </span>
        </header>
        <div className="max-w-4xl px-4 py-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
