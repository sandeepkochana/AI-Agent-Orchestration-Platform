import { useEffect, useRef } from 'react'
import clsx from 'clsx'

interface LogEntry {
  type?: string
  log_type?: string
  agent_name?: string
  content?: string
  status?: string
  execution_id?: string
  timestamp?: string
  channel?: string
  direction?: string
  [key: string]: unknown
}

interface Props {
  logs: LogEntry[]
  className?: string
}

const LOG_COLORS: Record<string, string> = {
  tool_call: 'text-yellow-400',
  tool_result: 'text-green-400',
  error: 'text-red-400',
  message: 'text-gray-200',
  status: 'text-blue-400',
  channel_message: 'text-purple-400',
}

export default function LogViewer({ logs, className }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  if (!logs.length) {
    return (
      <div className={clsx('flex items-center justify-center text-gray-600 text-sm', className)}>
        No logs yet. Run an agent or workflow to see activity here.
      </div>
    )
  }

  return (
    <div className={clsx('overflow-y-auto font-mono text-xs space-y-0.5 p-3', className)}>
      {logs.map((log, i) => {
        const logType = log.log_type || log.type || 'message'
        const color = LOG_COLORS[logType] || 'text-gray-400'
        const time = log.timestamp
          ? new Date(log.timestamp).toLocaleTimeString()
          : new Date().toLocaleTimeString()

        return (
          <div key={i} className="flex gap-2 hover:bg-gray-800/50 px-1 rounded">
            <span className="text-gray-600 shrink-0">{time}</span>
            {log.agent_name && (
              <span className="text-brand-400 shrink-0">[{log.agent_name}]</span>
            )}
            <span className={clsx('break-all', color)}>
              {log.content || log.status || JSON.stringify(log)}
            </span>
          </div>
        )
      })}
      <div ref={endRef} />
    </div>
  )
}
