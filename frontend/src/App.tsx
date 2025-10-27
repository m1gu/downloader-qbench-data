import { Navigate, Route, Routes } from 'react-router-dom'
import { OverviewTab } from './features/overview/OverviewTab'
import { OperationalEfficiencyTab } from './features/operational/OperationalEfficiencyTab'
import { PriorityOrdersTab } from './features/priority/PriorityOrdersTab'
import { DashboardPage } from './pages/DashboardPage'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />}>
        <Route index element={<OverviewTab />} />
        <Route path="operational-efficiency" element={<OperationalEfficiencyTab />} />
        <Route path="priority-orders" element={<PriorityOrdersTab />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
