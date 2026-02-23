import { useEffect, useState } from 'react';
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar,
} from 'recharts';
import { api } from '../api/client';
import type { CommodityListItem, SDDeltaResult, FlowResult } from '../api/client';
import { Card, MetricCard, LoadingSpinner, PageHeader } from '../components/Cards';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

// Approximate consensus annual production/trade estimates (MT) for S&D tracking
// These are rough USDA/FAO-level figures used as defaults
const CONSENSUS_DEFAULTS: Record<string, { annual_mt: number; crop_year_start: string }> = {
  'HCT-0801-RCN-INSHELL':   { annual_mt: 3_800_000, crop_year_start: '2025-04-01' },
  'HCT-0801-CASHEW-KERNEL': { annual_mt: 800_000,   crop_year_start: '2025-04-01' },
  'HCT-1207-SESAME':        { annual_mt: 2_800_000, crop_year_start: '2025-01-01' },
  'HCT-1006-RICE-NONBASMATI': { annual_mt: 55_000_000, crop_year_start: '2025-01-01' },
  'HCT-1006-RICE-BASMATI':  { annual_mt: 8_000_000, crop_year_start: '2025-04-01' },
  'HCT-1201-SOYBEAN':       { annual_mt: 380_000_000, crop_year_start: '2025-03-01' },
  'HCT-1801-COCOA':         { annual_mt: 4_800_000, crop_year_start: '2025-10-01' },
  'HCT-1207-SHEA':          { annual_mt: 600_000,   crop_year_start: '2025-06-01' },
  'HCT-1511-PALMOIL':       { annual_mt: 78_000_000, crop_year_start: '2025-01-01' },
  'HCT-5201-COTTON':        { annual_mt: 25_000_000, crop_year_start: '2025-08-01' },
};

const SIGNAL_CONFIG: Record<string, { color: string; icon: typeof TrendingUp; label: string }> = {
  OVER_SHIPPING:   { color: 'var(--accent-red)',   icon: TrendingDown, label: 'Over-Shipping — Bearish' },
  SLIGHTLY_OVER:   { color: 'var(--accent-amber)', icon: TrendingDown, label: 'Slightly Over — Watch' },
  ON_TRACK:        { color: 'var(--accent-green)',  icon: Minus,        label: 'On Track' },
  SLIGHTLY_UNDER:  { color: 'var(--accent-amber)', icon: TrendingUp,   label: 'Slightly Under — Watch' },
  UNDER_SHIPPING:  { color: 'var(--accent-cyan)',   icon: TrendingUp,   label: 'Under-Shipping — Bullish' },
};

interface SDAnalysis {
  commodity: CommodityListItem;
  delta: SDDeltaResult | null;
  flows: FlowResult | null;
  error?: string;
}

export default function SupplyDemand() {
  const [analyses, setAnalyses] = useState<Map<string, SDAnalysis>>(new Map());
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    api.listCommodities()
      .then((d) => {
        // Auto-run S&D for all commodities that have data
        const withData = d.commodities.filter(c => c.record_count > 0);
        if (withData.length > 0) {
          runAnalyses(withData);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const runAnalyses = async (items: CommodityListItem[]) => {
    const end = new Date().toISOString().slice(0, 10);
    const start = new Date(Date.now() - 180 * 86400000).toISOString().slice(0, 10);

    for (const c of items) {
      const defaults = CONSENSUS_DEFAULTS[c.hct_id];
      if (!defaults) continue;

      try {
        const [delta, flows] = await Promise.all([
          api.sdDelta({
            hct_id: c.hct_id,
            consensus_annual_mt: defaults.annual_mt,
            crop_year_start: defaults.crop_year_start,
          }).catch(() => null),
          api.sdFlows({
            hct_id: c.hct_id,
            start_date: start,
            end_date: end,
          }).catch(() => null),
        ]);

        setAnalyses(prev => {
          const next = new Map(prev);
          next.set(c.hct_id, { commodity: c, delta, flows });
          return next;
        });

        if (!selectedId) setSelectedId(c.hct_id);
      } catch {
        setAnalyses(prev => {
          const next = new Map(prev);
          next.set(c.hct_id, { commodity: c, delta: null, flows: null, error: 'Failed to load' });
          return next;
        });
      }
    }
  };

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;

  const selected = selectedId ? analyses.get(selectedId) : null;
  const allAnalyses = Array.from(analyses.values()).filter(a => a.delta);

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title="Supply & Demand Tracker"
        subtitle="The killer signal — actual trade flows vs. consensus expectations reveal hidden supply imbalances"
      />

      {/* Signal overview cards */}
      {allAnalyses.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
          {allAnalyses.map(a => {
            const d = a.delta!;
            const config = SIGNAL_CONFIG[d.signal] || SIGNAL_CONFIG.ON_TRACK;
            const Icon = config.icon;
            const isSelected = a.commodity.hct_id === selectedId;

            return (
              <Card
                key={a.commodity.hct_id}
                className={`cursor-pointer transition-colors ${isSelected ? 'ring-1 ring-cyan-500/50' : 'hover:border-cyan-800'}`}
              >
                <div onClick={() => setSelectedId(a.commodity.hct_id)}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {a.commodity.hct_name}
                    </span>
                    <Icon className="w-4 h-4" style={{ color: config.color }} />
                  </div>

                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-xl font-semibold tabular-nums" style={{ color: config.color }}>
                      {d.delta_pct > 0 ? '+' : ''}{d.delta_pct}%
                    </span>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      vs consensus
                    </span>
                  </div>

                  <div className="text-[10px] px-2 py-0.5 rounded inline-block"
                    style={{ background: `${config.color}20`, color: config.color }}>
                    {config.label}
                  </div>

                  <div className="flex justify-between mt-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                    <span>{d.crop_year_progress_pct}% crop year</span>
                    <span>{d.record_count} records</span>
                  </div>

                  {/* Mini progress bar */}
                  <div className="mt-2 flex gap-1 items-center">
                    <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                      <div className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(d.crop_year_progress_pct, 100)}%`,
                          background: config.color,
                        }}
                      />
                    </div>
                    <span className="text-[10px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      {(d.actual_cumulative_mt / 1000).toFixed(0)}K MT
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {allAnalyses.length === 0 && !loading && (
        <Card className="mb-6">
          <div className="flex items-center gap-3 py-6">
            <AlertTriangle className="w-5 h-5" style={{ color: 'var(--accent-amber)' }} />
            <div>
              <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                No supply-demand data available yet
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                S&D analysis requires trade flow data. Data will load automatically on the first visit,
                or you can fetch specific commodities from the Data page.
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Detailed view for selected commodity */}
      {selected?.delta && (
        <>
          {/* Key metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <MetricCard
              label="Actual Cumulative"
              value={`${(selected.delta.actual_cumulative_mt / 1000).toFixed(1)}K`}
              sub="MT shipped"
              accent="cyan"
            />
            <MetricCard
              label="Expected (Pro-Rata)"
              value={`${(selected.delta.expected_cumulative_mt / 1000).toFixed(1)}K`}
              sub="MT by consensus"
              accent="blue"
            />
            <MetricCard
              label="Delta"
              value={`${selected.delta.delta_mt > 0 ? '+' : ''}${(selected.delta.delta_mt / 1000).toFixed(1)}K`}
              sub={`${selected.delta.delta_pct > 0 ? '+' : ''}${selected.delta.delta_pct}% vs expected`}
              accent={selected.delta.delta_pct > 5 ? 'red' : selected.delta.delta_pct < -5 ? 'green' : 'amber'}
            />
            <MetricCard
              label="Consensus Annual"
              value={`${(selected.delta.consensus_annual_mt / 1_000_000).toFixed(1)}M`}
              sub="MT/year (USDA/FAO)"
            />
          </div>

          {/* Implication callout */}
          <Card className="mb-6">
            <div className="flex items-start gap-3">
              {(() => {
                const config = SIGNAL_CONFIG[selected.delta.signal] || SIGNAL_CONFIG.ON_TRACK;
                const Icon = config.icon;
                return (
                  <>
                    <Icon className="w-5 h-5 mt-0.5" style={{ color: config.color }} />
                    <div>
                      <div className="text-sm font-medium" style={{ color: config.color }}>
                        {config.label}
                      </div>
                      <div className="text-sm mt-1" style={{ color: 'var(--text-primary)' }}>
                        {selected.delta.implication}
                      </div>
                      <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                        {selected.commodity.hct_name} is at {selected.delta.crop_year_progress_pct}% of crop year with{' '}
                        {selected.delta.delta_pct > 0 ? 'more' : 'less'} supply than the market expects.
                      </div>
                    </div>
                  </>
                );
              })()}
            </div>
          </Card>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            {/* Cumulative flow chart */}
            {selected.flows && selected.flows.daily_series.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Cumulative Trade Flow (MT)
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={selected.flows.daily_series.filter((_, i) =>
                    i % Math.max(1, Math.floor(selected.flows!.daily_series.length / 90)) === 0
                  ).map(d => ({ ...d, date: d.date.slice(5) }))}>
                    <defs>
                      <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#94a3b8' }}
                      formatter={(value: unknown) => [`${Number(value).toLocaleString()} MT`, 'Cumulative']}
                    />
                    <Area type="monotone" dataKey="cumulative_volume_mt" stroke="#06b6d4"
                      fill="url(#flowGrad)" strokeWidth={2} name="Cumulative MT" />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>
            )}

            {/* Daily volume bar chart */}
            {selected.flows && selected.flows.daily_series.length > 0 && (
              <Card>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                  Daily Shipment Volumes (MT)
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={selected.flows.daily_series.filter(d => d.daily_volume_mt > 0).map(d => ({
                    ...d, date: d.date.slice(5)
                  }))}>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }}
                    />
                    <Bar dataKey="daily_volume_mt" fill="#3b82f6" radius={[2, 2, 0, 0]} name="Volume MT" />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            )}
          </div>

          {/* Country breakdown */}
          {selected.delta.country_breakdown.length > 0 && (
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                Source Country Breakdown
              </div>
              <div className="space-y-2">
                {selected.delta.country_breakdown.slice(0, 10).map(c => (
                  <div key={c.country} className="flex items-center gap-3">
                    <span className="text-xs w-24 truncate" style={{ color: 'var(--text-secondary)' }}>
                      {c.country}
                    </span>
                    <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                      <div className="h-full rounded-full" style={{
                        width: `${Math.min(c.share_pct, 100)}%`,
                        background: 'var(--accent-cyan)',
                      }} />
                    </div>
                    <span className="text-xs tabular-nums w-16 text-right" style={{ color: 'var(--text-primary)' }}>
                      {c.share_pct}%
                    </span>
                    <span className="text-xs tabular-nums w-20 text-right" style={{ color: 'var(--text-muted)' }}>
                      {(c.volume_mt / 1000).toFixed(1)}K MT
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
