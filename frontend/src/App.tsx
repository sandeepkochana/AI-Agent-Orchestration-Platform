import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useEffect } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import AgentsPage from './pages/Agents'
import WorkflowBuilderPage from './pages/WorkflowBuilder'
import MonitorPage from './pages/Monitor'
import MessagesPage from './pages/Messages'
import { useStore } from './store/useStore'

export default function App() {
  const connectWs = useStore(s => s.connectWs)
  useEffect(() => { connectWs() }, [connectWs])

  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: '#1e293b', color: '#f1f5f9', border: '1px solid #334155' },
        }}
      />
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/workflows" element={<WorkflowBuilderPage />} />
            <Route path="/monitor" element={<MonitorPage />} />
            <Route path="/messages" element={<MessagesPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
