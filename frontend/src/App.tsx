import { Navigate, Route, Routes } from 'react-router-dom'
import { OverviewTab } from './features/overview/OverviewTab'
import { OperationalEfficiencyTab } from './features/operational/OperationalEfficiencyTab'
import { PriorityOrdersTab } from './features/priority/PriorityOrdersTab'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'
import { ProtectedRoute } from './features/auth/ProtectedRoute'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      >
        <Route index element={<OverviewTab />} />
        <Route path="operational-efficiency" element={<OperationalEfficiencyTab />} />
        <Route path="priority-orders" element={<PriorityOrdersTab />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
