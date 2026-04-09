/**
 * App — router + layout + per-panel error boundaries (D-084) + SSE provider (Sprint 10).
 * S84: AuthProvider + ProtectedRoute + OAuth callback route.
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { SSEProvider } from './hooks/SSEContext'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { LoginPage } from './auth/LoginPage'
import { MissionListPage } from './pages/MissionListPage'
import { MissionDetailPage } from './pages/MissionDetailPage'
import { HealthPage } from './pages/HealthPage'
import { ApprovalsPage } from './pages/ApprovalsPage'
import { TelemetryPage } from './pages/TelemetryPage'
import { MonitoringPage } from './features/monitoring/MonitoringPage'
import { TemplatesPage } from './pages/TemplatesPage'
import { CostDashboardPage } from './pages/CostDashboardPage'
import { AgentHealthPage } from './pages/AgentHealthPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { NotFoundPage } from './pages/NotFoundPage'

function AppRoutes() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/missions" replace /> : <LoginPage />}
      />
      <Route
        path="/auth/callback"
        element={isAuthenticated ? <Navigate to="/missions" replace /> : <LoginPage />}
      />

      {/* Protected routes */}
      <Route path="/" element={<Navigate to="/missions" replace />} />
      <Route
        path="/missions"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Missions panel error">
                <MissionListPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/missions/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Mission detail panel error">
                <MissionDetailPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/health"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Health panel error">
                <HealthPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/approvals"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Approvals panel error">
                <ApprovalsPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/telemetry"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Telemetry panel error">
                <TelemetryPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/monitoring"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Monitoring panel error">
                <MonitoringPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Templates panel error">
                <TemplatesPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/costs"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Cost dashboard panel error">
                <CostDashboardPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/agents"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Agent health panel error">
                <AgentHealthPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Projects panel error">
                <ProjectsPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <Layout>
              <ErrorBoundary fallbackLabel="Project detail panel error">
                <ProjectDetailPage />
              </ErrorBoundary>
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <SSEProvider>
        <AppRoutes />
      </SSEProvider>
    </AuthProvider>
  )
}
