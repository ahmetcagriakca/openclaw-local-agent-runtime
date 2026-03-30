/**
 * App — router + layout + per-panel error boundaries (D-084) + SSE provider (Sprint 10).
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { SSEProvider } from './hooks/SSEContext'
import { MissionListPage } from './pages/MissionListPage'
import { MissionDetailPage } from './pages/MissionDetailPage'
import { HealthPage } from './pages/HealthPage'
import { ApprovalsPage } from './pages/ApprovalsPage'
import { TelemetryPage } from './pages/TelemetryPage'
import { MonitoringPage } from './features/monitoring/MonitoringPage'
import { TemplatesPage } from './pages/TemplatesPage'
import { CostDashboardPage } from './pages/CostDashboardPage'
import { AgentHealthPage } from './pages/AgentHealthPage'
import { NotFoundPage } from './pages/NotFoundPage'

export default function App() {
  return (
    <SSEProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/missions" replace />} />
          <Route
            path="/missions"
            element={
              <ErrorBoundary fallbackLabel="Missions panel error">
                <MissionListPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/missions/:id"
            element={
              <ErrorBoundary fallbackLabel="Mission detail panel error">
                <MissionDetailPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/health"
            element={
              <ErrorBoundary fallbackLabel="Health panel error">
                <HealthPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/approvals"
            element={
              <ErrorBoundary fallbackLabel="Approvals panel error">
                <ApprovalsPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/telemetry"
            element={
              <ErrorBoundary fallbackLabel="Telemetry panel error">
                <TelemetryPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/monitoring"
            element={
              <ErrorBoundary fallbackLabel="Monitoring panel error">
                <MonitoringPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/templates"
            element={
              <ErrorBoundary fallbackLabel="Templates panel error">
                <TemplatesPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/costs"
            element={
              <ErrorBoundary fallbackLabel="Cost dashboard panel error">
                <CostDashboardPage />
              </ErrorBoundary>
            }
          />
          <Route
            path="/agents"
            element={
              <ErrorBoundary fallbackLabel="Agent health panel error">
                <AgentHealthPage />
              </ErrorBoundary>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Layout>
    </SSEProvider>
  )
}
