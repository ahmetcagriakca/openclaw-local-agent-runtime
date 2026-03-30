/**
 * MonitoringPage — Sprint 16: integrated dashboard with real API data.
 *
 * Replaces mock data with real API hooks. Shows:
 * - KPI summary cards
 * - Mission list with filters
 * - Log viewer with level/stage/event filters
 * - Live event feed
 */
import { useState, useEffect } from 'react'
import { useMissions, type DashboardMission, type DashboardSummary } from './useMissions'
import { useLogs, type LogEntry } from './useLogs'
import { useLiveMission } from './useLiveMission'

// ── KPI Summary Cards ──────────────────────────────────────────

function SummaryCards({ summary }: { summary: DashboardSummary | null }) {
  if (!summary) return <div className="text-gray-400">Loading summary...</div>

  const cards = [
    { label: 'Missions', value: summary.total_missions, sub: `${summary.completed} completed` },
    { label: 'Total Tokens', value: summary.total_tokens.toLocaleString() },
    { label: 'Avg Duration', value: `${summary.avg_duration}s` },
    { label: 'Tool Calls', value: summary.total_tool_calls },
    { label: 'Budget Events', value: summary.total_budget_events },
    { label: 'Anomalies', value: summary.total_anomalies },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      {cards.map(c => (
        <div key={c.label} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
          <div className="text-xs text-gray-400 uppercase">{c.label}</div>
          <div className="text-xl font-bold text-white mt-1">{c.value}</div>
          {c.sub && <div className="text-xs text-gray-500">{c.sub}</div>}
        </div>
      ))}
    </div>
  )
}

// ── Mission Table ──────────────────────────────────────────────

function MissionTable({ missions }: { missions: DashboardMission[] }) {
  if (missions.length === 0) {
    return <div className="text-gray-400 p-4">No missions recorded yet.</div>
  }

  const statusColor: Record<string, string> = {
    completed: 'text-green-400',
    failed: 'text-red-400',
    aborted: 'text-yellow-400',
    executing: 'text-blue-400',
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-gray-400 uppercase border-b border-gray-700">
          <tr>
            <th className="px-3 py-2">ID</th>
            <th className="px-3 py-2">Goal</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Complexity</th>
            <th className="px-3 py-2">Tokens</th>
            <th className="px-3 py-2">Stages</th>
            <th className="px-3 py-2">Time</th>
          </tr>
        </thead>
        <tbody>
          {missions.map(m => (
            <tr key={m.id} className="border-b border-gray-800 hover:bg-gray-800/50">
              <td className="px-3 py-2 font-mono text-xs">{m.id}</td>
              <td className="px-3 py-2 max-w-xs truncate">{m.goal}</td>
              <td className={`px-3 py-2 ${statusColor[m.status] ?? 'text-gray-300'}`}>
                {m.status}
              </td>
              <td className="px-3 py-2">{m.complexity}</td>
              <td className="px-3 py-2 text-right">{m.tokens.toLocaleString()}</td>
              <td className="px-3 py-2 text-center">{m.stages}</td>
              <td className="px-3 py-2 text-xs text-gray-500">
                {new Date(m.ts).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Log Viewer ─────────────────────────────────────────────────

function LogViewer({ logs }: { logs: LogEntry[] }) {
  const levelColor: Record<string, string> = {
    INFO: 'text-blue-400',
    WARN: 'text-yellow-400',
    ERROR: 'text-red-400',
  }

  return (
    <div className="font-mono text-xs max-h-80 overflow-y-auto">
      {logs.length === 0 ? (
        <div className="text-gray-400 p-2">No log entries.</div>
      ) : (
        logs.map((entry, i) => (
          <div key={i} className="flex gap-2 py-0.5 border-b border-gray-800/50 hover:bg-gray-800/30">
            <span className="text-gray-500 w-20 shrink-0">
              {entry.ts ? new Date(entry.ts).toLocaleTimeString() : ''}
            </span>
            <span className={`w-12 shrink-0 ${levelColor[entry.level] ?? 'text-gray-300'}`}>
              {entry.level}
            </span>
            <span className="text-gray-300 w-36 shrink-0">{entry.event}</span>
            <span className="text-gray-500">{entry.stage ?? ''}</span>
            {entry.tool && <span className="text-cyan-400">{entry.tool}</span>}
          </div>
        ))
      )}
    </div>
  )
}

// ── Live Event Feed ────────────────────────────────────────────

function LiveFeed({ events, connected, onConnect, onDisconnect }: {
  events: Array<{ type: string; data: Record<string, unknown>; ts: string }>
  connected: boolean
  onConnect: () => void
  onDisconnect: () => void
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-gray-500'}`} />
        <span className="text-xs text-gray-400">{connected ? 'Connected' : 'Disconnected'}</span>
        <button
          onClick={connected ? onDisconnect : onConnect}
          className="text-xs px-2 py-0.5 rounded border border-gray-600 text-gray-300 hover:bg-gray-700"
        >
          {connected ? 'Disconnect' : 'Connect'}
        </button>
      </div>
      <div className="font-mono text-xs max-h-48 overflow-y-auto">
        {events.length === 0 ? (
          <div className="text-gray-400">No live events yet.</div>
        ) : (
          events.slice(-50).reverse().map((e, i) => (
            <div key={i} className="py-0.5 text-gray-300">
              <span className="text-gray-500">{new Date(e.ts).toLocaleTimeString()}</span>
              {' '}
              <span className="text-cyan-400">{e.type}</span>
              {' '}
              <span className="text-gray-500" title={JSON.stringify(e.data, null, 2)}>
                {JSON.stringify(e.data).slice(0, 80)}{JSON.stringify(e.data).length > 80 ? '...' : ''}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────

export function MonitoringPage() {
  const { missions, total, summary, loading, error, fetchMissions, fetchSummary } = useMissions()
  const { logs, total: logTotal, fetchLogs } = useLogs()
  const { events, connected, connect, disconnect } = useLiveMission()

  const [statusFilter, setStatusFilter] = useState('')
  const [complexityFilter, setComplexityFilter] = useState('')
  const [searchFilter, setSearchFilter] = useState('')
  const [logLevel, setLogLevel] = useState('')

  useEffect(() => {
    fetchMissions({
      status: statusFilter || undefined,
      complexity: complexityFilter || undefined,
      search: searchFilter || undefined,
    })
    fetchSummary()
  }, [statusFilter, complexityFilter, searchFilter, fetchMissions, fetchSummary])

  useEffect(() => {
    fetchLogs({ level: logLevel || undefined, limit: 100 })
  }, [logLevel, fetchLogs])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Monitoring Dashboard</h1>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-300 p-3 rounded">
          {error}
        </div>
      )}

      <SummaryCards summary={summary} />

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-3 py-1.5"
        >
          <option value="">All Status</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="aborted">Aborted</option>
        </select>
        <select
          value={complexityFilter}
          onChange={e => setComplexityFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-3 py-1.5"
        >
          <option value="">All Complexity</option>
          <option value="trivial">Trivial</option>
          <option value="medium">Medium</option>
          <option value="complex">Complex</option>
        </select>
        <input
          type="text"
          placeholder="Search missions..."
          value={searchFilter}
          onChange={e => setSearchFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-3 py-1.5 w-48"
        />
      </div>

      {/* Mission Table */}
      <div className="bg-gray-900 rounded-lg border border-gray-700">
        <div className="flex justify-between items-center px-4 py-2 border-b border-gray-700">
          <h2 className="text-sm font-semibold text-gray-300">Missions ({total})</h2>
        </div>
        {loading ? (
          <div className="p-4 text-gray-400">Loading...</div>
        ) : (
          <MissionTable missions={missions} />
        )}
      </div>

      {/* Two-column: Logs + Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Logs */}
        <div className="bg-gray-900 rounded-lg border border-gray-700">
          <div className="flex justify-between items-center px-4 py-2 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-gray-300">Structured Logs ({logTotal})</h2>
            <select
              value={logLevel}
              onChange={e => setLogLevel(e.target.value)}
              className="bg-gray-800 border border-gray-600 text-gray-300 text-xs rounded px-2 py-1"
            >
              <option value="">All Levels</option>
              <option value="INFO">INFO</option>
              <option value="WARN">WARN</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
          <div className="p-2">
            <LogViewer logs={logs} />
          </div>
        </div>

        {/* Live Feed */}
        <div className="bg-gray-900 rounded-lg border border-gray-700">
          <div className="px-4 py-2 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-gray-300">Live Events</h2>
          </div>
          <div className="p-2">
            <LiveFeed
              events={events}
              connected={connected}
              onConnect={connect}
              onDisconnect={disconnect}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
