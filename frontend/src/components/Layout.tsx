import { NavLink, Outlet } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  GitCompareArrows,
  Users,
  Search,
  ArrowLeftRight,
  Database,
  TrendingUp,
  Scale,
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: Activity, label: 'Signals' },
  { to: '/commodities', icon: BarChart3, label: 'Commodities' },
  { to: '/supply-demand', icon: Scale, label: 'S&D Tracker' },
  { to: '/corridors', icon: GitCompareArrows, label: 'Corridors' },
  { to: '/counterparty-search', icon: Search, label: 'Party Search' },
  { to: '/counterparty', icon: Users, label: 'Market Shares' },
  { to: '/arbitrage', icon: ArrowLeftRight, label: 'Arb Scanner' },
  { to: '/data', icon: Database, label: 'Data' },
];

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col border-r"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>
        <div className="px-4 py-5 flex items-center gap-2 border-b"
          style={{ borderColor: 'var(--border)' }}>
          <TrendingUp className="w-6 h-6 text-cyan-400" />
          <div>
            <div className="font-bold text-sm tracking-wide" style={{ color: 'var(--text-primary)' }}>
              HECTAR
            </div>
            <div className="text-[10px] tracking-widest uppercase" style={{ color: 'var(--text-muted)' }}>
              Commodity Intel
            </div>
          </div>
        </div>

        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400'
                    : 'hover:bg-white/5'
                }`
              }
              style={({ isActive }) => ({
                color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              })}
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 text-[10px] border-t" style={{
          color: 'var(--text-muted)', borderColor: 'var(--border)'
        }}>
          v1.0 &middot; Data as of today
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto" style={{ background: 'var(--bg-primary)' }}>
        <Outlet />
      </main>
    </div>
  );
}
