import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar,
} from 'recharts';
import { api } from '../api/client';
import type { CounterpartyProfile } from '../api/client';
import { Card, MetricCard, PageHeader, LoadingSpinner } from '../components/Cards';
import { Search, TrendingUp, TrendingDown, Minus, Package, MapPin } from 'lucide-react';

const HUNGER_CONFIG: Record<string, { color: string; icon: typeof TrendingUp; label: string }> = {
  INCREASING: { color: 'var(--accent-red)', icon: TrendingUp, label: 'Getting Hungrier' },
  STABLE: { color: 'var(--accent-green)', icon: Minus, label: 'Stable Appetite' },
  DECREASING: { color: 'var(--accent-cyan)', icon: TrendingDown, label: 'Pulling Back' },
};

export default function CounterpartySearch() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('name') || '');
  const [tradeCountry, setTradeCountry] = useState('INDIA');
  const [tradeType, setTradeType] = useState(searchParams.get('trade_type') || 'IMPORT');
  const [months, setMonths] = useState(6);
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<CounterpartyProfile | null>(null);
  const [error, setError] = useState('');

  // Auto-search if navigated with query params (from commodity detail click-through)
  useEffect(() => {
    const name = searchParams.get('name');
    const type = searchParams.get('trade_type');
    if (name && name.length >= 2) {
      setQuery(name);
      if (type) setTradeType(type);
      // Trigger search after state updates
      setTimeout(() => {
        handleSearchWith(name, type || tradeType);
      }, 0);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearchWith = async (name: string, type: string) => {
    if (name.trim().length < 2) return;
    setLoading(true);
    setError('');
    setProfile(null);
    try {
      const result = await api.counterpartySearch({
        name: name.trim(),
        trade_country: tradeCountry,
        trade_type: type,
        months,
      });
      if (result.status === 'NOT_FOUND') {
        setError(result.message || `No shipments found for "${name}"`);
      } else {
        setProfile(result);
      }
    } catch {
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (query.trim().length < 2) return;
    setLoading(true);
    setError('');
    setProfile(null);
    try {
      const result = await api.counterpartySearch({
        name: query.trim(),
        trade_country: tradeCountry,
        trade_type: tradeType,
        months,
      });
      if (result.status === 'NOT_FOUND') {
        setError(result.message || `No shipments found for "${query}"`);
      } else {
        setProfile(result);
      }
    } catch (e) {
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title="Counterparty Intelligence"
        subtitle="Search any buyer or seller to reveal their trading patterns, price behavior, and market position"
      />

      {/* Search form */}
      <Card className="mb-6">
        <div className="flex flex-col gap-3">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search company name (e.g. Olam, Cargill, Louis Dreyfus...)"
                className="w-full pl-10 pr-4 py-2 rounded-md text-sm border outline-none focus:ring-1 focus:ring-cyan-500"
                style={{
                  background: 'var(--bg-secondary)', borderColor: 'var(--border)',
                  color: 'var(--text-primary)',
                }}
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading || query.trim().length < 2}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
              style={{ background: 'var(--accent-cyan)', color: '#000' }}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div className="flex gap-3 flex-wrap">
            <select
              value={tradeCountry}
              onChange={(e) => setTradeCountry(e.target.value)}
              className="px-3 py-1.5 rounded text-xs border"
              style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            >
              <option value="INDIA">India</option>
              <option value="VIETNAM">Vietnam</option>
              <option value="NIGERIA">Nigeria</option>
              <option value="GHANA">Ghana</option>
              <option value="ETHIOPIA">Ethiopia</option>
              <option value="TANZANIA">Tanzania</option>
              <option value="INDONESIA">Indonesia</option>
            </select>
            <select
              value={tradeType}
              onChange={(e) => setTradeType(e.target.value)}
              className="px-3 py-1.5 rounded text-xs border"
              style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            >
              <option value="IMPORT">Buyer (Importer)</option>
              <option value="EXPORT">Seller (Exporter)</option>
            </select>
            <select
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="px-3 py-1.5 rounded text-xs border"
              style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            >
              <option value={3}>3 months</option>
              <option value={6}>6 months</option>
              <option value={12}>12 months</option>
            </select>
          </div>
        </div>
      </Card>

      {error && (
        <Card className="mb-6">
          <div className="text-sm text-center py-4" style={{ color: 'var(--accent-amber)' }}>
            {error}
          </div>
        </Card>
      )}

      {loading && <LoadingSpinner />}

      {profile && (
        <>
          {/* Header + Hunger Signal */}
          <Card className="mb-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {profile.counterparty_name}
                </h2>
                <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  {profile.trade_type === 'IMPORT' ? 'Buyer' : 'Seller'} in {profile.trade_country}
                  {' · '}Data from {profile.summary.date_range.earliest} to {profile.summary.date_range.latest}
                  {' · '}Source: {profile.data_source === 'api' ? 'Live API' : 'Cached'}
                </div>
              </div>
              {(() => {
                const h = HUNGER_CONFIG[profile.summary.hunger_signal] || HUNGER_CONFIG.STABLE;
                const Icon = h.icon;
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-md"
                    style={{ background: `${h.color}15` }}>
                    <Icon className="w-4 h-4" style={{ color: h.color }} />
                    <span className="text-xs font-medium" style={{ color: h.color }}>
                      {h.label}
                    </span>
                  </div>
                );
              })()}
            </div>
          </Card>

          {/* Key metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <MetricCard
              label="Total Shipments"
              value={profile.summary.total_shipments}
              accent="cyan"
            />
            <MetricCard
              label="Total Volume"
              value={`${(profile.summary.total_volume_mt / 1000).toFixed(1)}K MT`}
              accent="blue"
            />
            <MetricCard
              label="Total Value"
              value={`$${(profile.summary.total_value_usd / 1000).toFixed(0)}K`}
              accent="green"
            />
            <MetricCard
              label="Avg Price"
              value={profile.summary.avg_price_per_mt ? `$${profile.summary.avg_price_per_mt.toLocaleString()}/MT` : '---'}
              sub={profile.market_comparison[0]
                ? `Market: $${profile.market_comparison[0].market_price.toLocaleString()}/MT`
                : undefined}
              accent={
                profile.market_comparison[0] && profile.summary.avg_price_per_mt
                  ? profile.summary.avg_price_per_mt > profile.market_comparison[0].market_price
                    ? 'red' : 'green'
                  : 'cyan'
              }
            />
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            {/* Volume trend */}
            {profile.volume_series.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Monthly Volume Trend (MT)
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={profile.volume_series}>
                    <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="volume_mt" fill="#3b82f6" radius={[3, 3, 0, 0]} name="Volume MT" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            )}

            {/* Price trend */}
            {profile.price_series.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Purchase Price Trend (USD/MT)
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={profile.price_series.slice(-50).map(d => ({ ...d, date: d.date.slice(5) }))}>
                    <defs>
                      <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }} />
                    <Area type="monotone" dataKey="price_usd_per_mt" stroke="#06b6d4" fill="url(#priceGrad)" strokeWidth={2} name="USD/MT" />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
            )}
          </div>

          {/* Breakdowns row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            {/* Commodity breakdown */}
            {profile.commodity_breakdown.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  <Package className="w-3 h-3 inline mr-1" /> Commodities Traded
                </div>
                <div className="space-y-2">
                  {profile.commodity_breakdown.slice(0, 8).map(c => (
                    <div key={c.hct_id} className="flex items-center justify-between">
                      <span className="text-xs truncate flex-1" style={{ color: 'var(--text-secondary)' }}>
                        {c.name}
                      </span>
                      <span className="text-xs tabular-nums ml-2" style={{ color: 'var(--text-primary)' }}>
                        {c.shipments} shipments
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Geography breakdown */}
            {profile.geography_breakdown.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  <MapPin className="w-3 h-3 inline mr-1" /> Source Countries
                </div>
                <div className="space-y-2">
                  {profile.geography_breakdown.slice(0, 8).map(g => (
                    <div key={g.country} className="flex items-center gap-2">
                      <span className="text-xs w-28 truncate" style={{ color: 'var(--text-secondary)' }}>
                        {g.country}
                      </span>
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                        <div className="h-full rounded-full" style={{ width: `${g.share_pct}%`, background: 'var(--accent-cyan)' }} />
                      </div>
                      <span className="text-xs tabular-nums w-10 text-right" style={{ color: 'var(--text-primary)' }}>
                        {g.share_pct}%
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Quality breakdown */}
            {profile.quality_breakdown.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Quality Grades
                </div>
                <div className="space-y-2">
                  {profile.quality_breakdown.slice(0, 8).map(q => (
                    <div key={q.grade} className="flex items-center justify-between">
                      <span className="text-xs truncate flex-1" style={{ color: 'var(--text-secondary)' }}>
                        {q.grade}
                      </span>
                      <span className="text-xs tabular-nums ml-2" style={{ color: 'var(--text-primary)' }}>
                        {q.count}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Recent shipments table */}
          {profile.recent_shipments.length > 0 && (
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                Recent Shipments
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ color: 'var(--text-muted)' }}>
                      <th className="text-left py-2 pr-3">Date</th>
                      <th className="text-left py-2 pr-3">Commodity</th>
                      <th className="text-left py-2 pr-3">Origin</th>
                      <th className="text-right py-2 pr-3">Qty (MT)</th>
                      <th className="text-right py-2 pr-3">Price ($/MT)</th>
                      <th className="text-left py-2">Port</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.recent_shipments.map((s, i) => (
                      <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                        <td className="py-2 pr-3 tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                          {s.date}
                        </td>
                        <td className="py-2 pr-3" style={{ color: 'var(--text-primary)' }}>
                          {s.commodity}
                        </td>
                        <td className="py-2 pr-3" style={{ color: 'var(--text-secondary)' }}>
                          {s.origin || s.destination || '-'}
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums" style={{ color: 'var(--text-primary)' }}>
                          {s.quantity_mt ? s.quantity_mt.toFixed(1) : '-'}
                        </td>
                        <td className="py-2 pr-3 text-right tabular-nums" style={{ color: 'var(--accent-cyan)' }}>
                          {s.fob_usd_per_mt ? `$${s.fob_usd_per_mt.toFixed(0)}` : '-'}
                        </td>
                        <td className="py-2" style={{ color: 'var(--text-muted)' }}>
                          {s.port || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
