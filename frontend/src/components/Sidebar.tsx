import { NavLink } from 'react-router-dom'
import { Bot, GitBranch, Activity, MessageSquare, LayoutDashboard, Zap } from 'lucide-react'
import { useStore } from '../store/useStore'
import clsx from 'clsx'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/workflows', icon: GitBranch, label: 'Workflows' },
  { to: '/monitor', icon: Activity, label: 'Monitor' },
  { to: '/messages', icon: MessageSquare, label: 'Messages' },
]

export default function Sidebar() {
  const wsConnected = useStore(s => s.wsConnected)

  return (
    <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col min-h-screen">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Zap className="text-brand-500" size={22} />
          <span className="font-bold text-white text-sm leading-tight">AI Agent<br/>Platform</span>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx('flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors', {
                'bg-brand-600 text-white': isActive,
                'text-gray-400 hover:text-white hover:bg-gray-800': !isActive,
              })
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-800 flex items-center gap-2 text-xs text-gray-500">
        <div className={clsx('w-2 h-2 rounded-full', wsConnected ? 'bg-green-400' : 'bg-red-400')} />
        {wsConnected ? 'Live' : 'Disconnected'}
      </div>
    </aside>
  )
}
