import { useMemo } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import './dashboard.css'

type NavItem = {
  label: string
  to?: string
  disabled?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Overview', to: '/dashboard' },
  { label: 'Operational Efficiency', to: '/dashboard/operational-efficiency' },
  { label: 'Priority Orders', to: '/dashboard/priority-orders' },
]

export function DashboardPage() {
  const location = useLocation()

  const heroCopy = useMemo(() => {
    if (location.pathname.includes('operational-efficiency')) {
      return {
        eyebrow: 'Operational Efficiency',
        title: 'Operational Efficiency',
        subtitle: 'Track throughput, cycle times, and funnel health to spot bottlenecks early.',
      }
    }
    if (location.pathname.includes('priority-orders')) {
      return {
        eyebrow: 'Priority Orders',
        title: 'Priority Orders',
        subtitle: 'Monitor overdue orders, warning signals, and ready-to-report samples to stay ahead of SLAs.',
      }
    }
    return {
      eyebrow: 'Overview',
      title: 'MCRLabs Metrics',
      subtitle: 'Monitor QBench activity with key metrics, turnaround trends, and highlighted customers.',
    }
  }, [location.pathname])

  return (
    <div className="dashboard">
      <header className="dashboard__topbar">
        <div className="dashboard__branding">
          <span className="dashboard__badge">Q</span>
          <div className="dashboard__identity">
            <span className="dashboard__environment">MCRLabs Metrics</span>
          </div>
        </div>

        <nav className="dashboard__tabs" aria-label="Dashboard sections">
          {NAV_ITEMS.map((item) =>
            item.to ? (
              <NavLink
                key={item.label}
                to={item.to}
                className={({ isActive }) =>
                  ['dashboard__tab', isActive ? 'dashboard__tab--active' : null].filter(Boolean).join(' ')
                }
                end
              >
                {item.label}
              </NavLink>
            ) : (
              <span key={item.label} className="dashboard__tab dashboard__tab--disabled">
                {item.label}
              </span>
            ),
          )}
        </nav>
      </header>

      <main className="dashboard__content">
        <section className="dashboard__hero">
          <p className="dashboard__eyebrow">{heroCopy.eyebrow}</p>
          <h1 className="dashboard__title">{heroCopy.title}</h1>
          <p className="dashboard__subtitle">{heroCopy.subtitle}</p>
        </section>
        <Outlet />
      </main>
    </div>
  )
}
