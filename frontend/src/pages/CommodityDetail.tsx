import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, AreaChart, Area,
} from 'recharts';
import { api } from '../api/client';
import type { DeepDiveResult, EnrichedEntity } from '../api/client';
import { Card, LoadingSpinner, PageHeader } from '../components/Cards';
import {
  ArrowLeft, TrendingUp, TrendingDown, Minus, ChevronRight,
  ArrowUpRight, ArrowDownRight,
} from 'lucide-react';

const MOMENTUM_CONFIG: Record<string, { color: string; icon: typeof TrendingUp }> = {
  ACCELERATING:      { color: 'var(--accent-red)',   icon: ArrowUpRight },
  PICKING_UP:        { color: 'var(--accent-green)', icon: TrendingUp },
  STEADY:            { color: 'var(--text-secondary)', icon: Minus },
  SLOWING:           { color: 'var(--accent-amber)', icon: TrendingDown },
  DROPPING:          { color: 'var(--accent-red)',   icon: ArrowDownRight },
  INSUFFICIENT_DATA: { color: 'var(--text-muted)',   icon: Minus },
};

function formatDate(iso: string) {
  if (!iso) return '';
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function CommodityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DeepDiveResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const end = new Date().toISOString().slice(0, 10);
    const start = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);

    api.commodityDeepDive({ hct_id: id, start_date: start, end_date: end })
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;
  if (!data) return <div className="p-6" style={{ color: 'var(--text-muted)' }}>No data available</div>;

  const momentum = data.volume_momentum;
  const momConfig = MOMENTUM_CONFIG[momentum.signal] || MOMENTUM_CONFIG.INSUFFICIENT_DATA;
  const MomIcon = momConfig.icon;

  const priceSeries = data.ipc_series
    .filter((p) => p.price_usd_per_mt !== null)
    .map((p) => ({ ...p, date: p.date?.slice(5) }));

  const volumeSeries = data.volume_summary.daily_series
    .filter((d) => d.daily_volume_mt > 0)
    .map((d) => ({ ...d, date: d.date.slice(5) }));

  const handleCounterpartyClick = (name: string, type: 'buyer' | 'seller') => {
    const params = new URLSearchParams({
      name,
      trade_type: type === 'buyer' ? 'IMPORT' : 'EXPORT',
    });
    navigate(`/counterparty-search?${params.toString()}`);
  };

  return (
    <div className="p-6 max-w-6xl">
      <button onClick={() => navigate('/commodities')}
        className="flex items-center gap-1 text-xs mb-4 hover:underline"
        style={{ color: 'var(--accent-cyan)' }}>
        <ArrowLeft className="w-3 h-3" /> Back to commodities
      </button>

      <PageHeader
        title={data.commodity.hct_name}
        subtitle={`${data.commodity.hct_group} | ${data.volume_summary.record_count.toLocaleString()} shipments`}
      />

      {/* Period banner */}
      <div className="text-xs mb-6 px-3 py-2 rounded-md inline-block"
        style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
        Showing data from <span style={{ color: 'var(--text-primary)' }}>{formatDate(data.period.start)}</span>
        {' '}to <span style={{ color: 'var(--text-primary)' }}>{formatDate(data.period.end)}</span>
        {' '}({data.volume_summary.record_count} records)
      </div>

      {/* ── Section 1: Price by Grade × Origin ────────────────── */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            Price by Quality & Origin
          </div>
          <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            FOB USD/MT | {formatDate(data.period.start)} – {formatDate(data.period.end)}
          </div>
        </div>

        {data.price_by_grade.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-3 font-medium">Quality / Grade</th>
                  <th className="text-left py-2 pr-3 font-medium">Origin</th>
                  <th className="text-right py-2 pr-3 font-medium">FOB $/MT</th>
                  <th className="text-right py-2 pr-3 font-medium">Range</th>
                  <th className="text-right py-2 pr-3 font-medium">Volume (MT)</th>
                  <th className="text-right py-2 font-medium">Shipments</th>
                </tr>
              </thead>
              <tbody>
                {data.price_by_grade.map((row, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-2.5 pr-3" style={{ color: 'var(--text-primary)' }}>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{ background: 'var(--bg-secondary)' }}>
                        {row.grade}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3" style={{ color: 'var(--text-secondary)' }}>
                      {row.origin}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums font-medium"
                      style={{ color: row.fob_usd_per_mt ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                      {row.fob_usd_per_mt ? `$${row.fob_usd_per_mt.toLocaleString()}` : '—'}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      {row.price_range
                        ? `$${row.price_range.min.toLocaleString()} – $${row.price_range.max.toLocaleString()}`
                        : '—'}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-primary)' }}>
                      {row.volume_mt > 1000
                        ? `${(row.volume_mt / 1000).toFixed(1)}K`
                        : row.volume_mt.toFixed(1)}
                    </td>
                    <td className="py-2.5 text-right tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {row.shipments}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm py-6 text-center" style={{ color: 'var(--text-muted)' }}>
            No price data available for this period
          </div>
        )}
      </Card>

      {/* ── Section 2: Volume Momentum ────────────────────────── */}
      <Card className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            Volume Momentum
          </div>
          <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            Week-over-week comparison
          </div>
        </div>

        <div className="flex items-center gap-3 mb-4">
          <MomIcon className="w-5 h-5" style={{ color: momConfig.color }} />
          <div>
            <div className="text-sm font-medium" style={{ color: momConfig.color }}>
              {momentum.description}
            </div>
            <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              Last 7 days: {momentum.recent_7d_mt.toLocaleString()} MT ({momentum.recent_7d_shipments} shipments)
              {' · '}Prior 7 days: {momentum.prior_7d_mt.toLocaleString()} MT ({momentum.prior_7d_shipments} shipments)
            </div>
          </div>
          {momentum.change_pct !== null && (
            <div className="ml-auto text-xl font-semibold tabular-nums" style={{ color: momConfig.color }}>
              {momentum.change_pct > 0 ? '+' : ''}{momentum.change_pct}%
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md p-3" style={{ background: 'var(--bg-secondary)' }}>
            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
              This week ({formatDate(momentum.recent_period.split(' to ')[0])} – {formatDate(momentum.recent_period.split(' to ')[1])})
            </div>
            <div className="text-lg font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
              {momentum.recent_7d_mt.toLocaleString()} MT
            </div>
          </div>
          <div className="rounded-md p-3" style={{ background: 'var(--bg-secondary)' }}>
            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
              Prior week ({formatDate(momentum.prior_period.split(' to ')[0])} – {formatDate(momentum.prior_period.split(' to ')[1])})
            </div>
            <div className="text-lg font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
              {momentum.prior_7d_mt.toLocaleString()} MT
            </div>
          </div>
        </div>
      </Card>

      {/* ── Section 3: Price Trend + Volume Charts ────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Price Trend (FOB USD/MT)
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {formatDate(data.period.start)} – {formatDate(data.period.end)}
            </div>
          </div>
          {priceSeries.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={priceSeries}>
                <defs>
                  <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#94a3b8' }}
                  formatter={(value: unknown) => [`$${Number(value).toLocaleString()}/MT`, 'FOB Price']}
                />
                <Area type="monotone" dataKey="price_usd_per_mt" stroke="#06b6d4"
                  fill="url(#priceGrad)" strokeWidth={2} name="Price $/MT" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm" style={{ color: 'var(--text-muted)' }}>
              No price data in period
            </div>
          )}
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Daily Shipment Volumes (MT)
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {formatDate(data.period.start)} – {formatDate(data.period.end)}
            </div>
          </div>
          {volumeSeries.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={volumeSeries}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="daily_volume_mt" fill="#3b82f6" radius={[2, 2, 0, 0]} name="Volume MT" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-sm" style={{ color: 'var(--text-muted)' }}>
              No volume data
            </div>
          )}
        </Card>
      </div>

      {/* ── Section 4: Top Buyers & Sellers (clickable, with grade/price) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <CounterpartyTable
          title="Top Buyers"
          subtitle={`${formatDate(data.period.start)} – ${formatDate(data.period.end)}`}
          entities={data.top_buyers}
          partyType="buyer"
          onEntityClick={handleCounterpartyClick}
        />
        <CounterpartyTable
          title="Top Sellers"
          subtitle={`${formatDate(data.period.start)} – ${formatDate(data.period.end)}`}
          entities={data.top_sellers}
          partyType="seller"
          onEntityClick={handleCounterpartyClick}
        />
      </div>

      {/* ── Section 5: Origin Breakdown ───────────────────────── */}
      {data.volume_summary.country_breakdown.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Origin Breakdown by Volume
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {formatDate(data.period.start)} – {formatDate(data.period.end)}
            </div>
          </div>
          <div className="space-y-2">
            {data.volume_summary.country_breakdown.slice(0, 10).map(c => (
              <div key={c.country} className="flex items-center gap-3">
                <span className="text-xs w-28 truncate" style={{ color: 'var(--text-secondary)' }}>
                  {c.country}
                </span>
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                  <div className="h-full rounded-full" style={{
                    width: `${Math.min(c.share_pct, 100)}%`,
                    background: 'var(--accent-cyan)',
                  }} />
                </div>
                <span className="text-xs tabular-nums w-12 text-right" style={{ color: 'var(--text-primary)' }}>
                  {c.share_pct}%
                </span>
                <span className="text-xs tabular-nums w-20 text-right" style={{ color: 'var(--text-muted)' }}>
                  {c.volume_mt > 1000
                    ? `${(c.volume_mt / 1000).toFixed(1)}K MT`
                    : `${c.volume_mt.toFixed(0)} MT`}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}


/* ── Counterparty Table Component ──────────────────────────────── */

function CounterpartyTable({
  title,
  subtitle,
  entities,
  partyType,
  onEntityClick,
}: {
  title: string;
  subtitle: string;
  entities: EnrichedEntity[];
  partyType: 'buyer' | 'seller';
  onEntityClick: (name: string, type: 'buyer' | 'seller') => void;
}) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          {title}
        </div>
        <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
          {subtitle}
        </div>
      </div>

      {entities.length > 0 ? (
        <div className="space-y-3">
          {entities.slice(0, 8).map((e) => (
            <div key={e.entity}
              className="group rounded-md p-2.5 -mx-1 cursor-pointer transition-colors hover:bg-white/5"
              onClick={() => onEntityClick(e.entity, partyType)}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-medium truncate max-w-[180px]" style={{ color: 'var(--text-primary)' }}>
                    {e.entity}
                  </span>
                  <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: 'var(--accent-cyan)' }} />
                </div>
                <div className="flex items-center gap-2 text-xs tabular-nums">
                  <span style={{ color: 'var(--accent-cyan)' }}>
                    {e.avg_price_per_mt ? `$${e.avg_price_per_mt.toLocaleString()}/MT` : '—'}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {e.market_share_pct}%
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {/* Volume */}
                <span className="text-[10px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
                  {e.volume_mt > 1000 ? `${(e.volume_mt / 1000).toFixed(1)}K MT` : `${e.volume_mt.toFixed(0)} MT`}
                  {' · '}{e.shipments} ship.
                </span>

                {/* Quality badges */}
                {e.top_grades.length > 0 && e.top_grades[0].grade !== 'Unknown' && (
                  <>
                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>·</span>
                    {e.top_grades.slice(0, 2).map(g => (
                      <span key={g.grade} className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                        {g.grade} ({g.count})
                      </span>
                    ))}
                  </>
                )}

                {/* Origin badges */}
                {e.top_origins.length > 0 && (
                  <>
                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>·</span>
                    {e.top_origins.slice(0, 2).map(o => (
                      <span key={o.country} className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                        {o.country}
                      </span>
                    ))}
                  </>
                )}
              </div>

              {/* Market share bar */}
              <div className="mt-1.5 h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                <div className="h-full rounded-full transition-all" style={{
                  width: `${Math.min(e.market_share_pct, 100)}%`,
                  background: partyType === 'buyer' ? 'var(--accent-cyan)' : 'var(--accent-blue)',
                }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm py-4 text-center" style={{ color: 'var(--text-muted)' }}>
          No data
        </div>
      )}
    </Card>
  );
}
