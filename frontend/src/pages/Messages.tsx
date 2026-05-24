import { useEffect, useState } from 'react'
import { msgApi } from '../api/client'
import type { ChannelMessage } from '../api/client'
import { MessageSquare, RefreshCw } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function MessagesPage() {
  const [messages, setMessages] = useState<ChannelMessage[]>([])
  const [channel, setChannel] = useState<string>('')
  const liveLogs = useStore(s => s.liveLogs)

  const load = () => msgApi.list(channel || undefined).then(setMessages)
  useEffect(() => { load() }, [channel])

  // Refresh on new channel_message ws events
  useEffect(() => {
    const last = liveLogs[liveLogs.length - 1]
    if (last?.type === 'channel_message') load()
  }, [liveLogs])

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Messages</h1>
          <p className="text-gray-400 text-sm">Channel conversation history</p>
        </div>
        <div className="flex gap-2">
          <select
            className="input text-sm"
            value={channel}
            onChange={e => setChannel(e.target.value)}
          >
            <option value="">All channels</option>
            <option value="telegram">Telegram</option>
            <option value="slack">Slack</option>
            <option value="internal">Internal</option>
          </select>
          <button onClick={load} className="btn-ghost text-xs flex items-center gap-1">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {messages.length === 0 && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-10 text-center">
          <MessageSquare size={40} className="mx-auto text-gray-600 mb-3" />
          <p className="text-gray-400">No messages yet. Connect a channel and start chatting.</p>
        </div>
      )}

      <div className="space-y-2">
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[70%] rounded-xl px-4 py-3 ${
              msg.direction === 'outbound'
                ? 'bg-brand-600/20 border border-brand-700'
                : 'bg-gray-800 border border-gray-700'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  msg.channel === 'telegram' ? 'bg-blue-700/30 text-blue-400'
                  : msg.channel === 'slack' ? 'bg-purple-700/30 text-purple-400'
                  : 'bg-gray-700 text-gray-400'
                }`}>
                  {msg.channel}
                </span>
                <span className="text-xs text-gray-500">{msg.direction}</span>
                <span className="text-xs text-gray-600">{new Date(msg.created_at).toLocaleTimeString()}</span>
              </div>
              <p className="text-sm text-gray-200">{msg.content}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
