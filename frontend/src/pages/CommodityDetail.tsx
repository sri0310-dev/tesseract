import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
} from 'recharts';
import { api, DeepDiveResult } from '../api/client';
import { Card, MetricCard, ConfidenceBadge, LoadingSpinner, PageHeader } from '../components/Cards';
import { ArrowLeft } from 'lucide-react';

const COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#f59e0b', '#22c55e', '#ef4444', '#ec4899', '#14b8a6'];

export default function CommodityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DeepDiveResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const end = new Date().toISOString().slice(0, 10);
    const start = new Date(Date.now() - 180 * 86400000).toISOString().slice(0, 10);

    api.commodityDeepDive({ hct_id: id, start_date: start, end_date: end })
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;
  if (!data) return <div className="p-6" style={{ color: 'var(--text-muted)' }}>No data available</div>;

  const ipc = data.current_ipc;
  const fvi = data.fvi;
  const priceSeries = data.ipc_series
    .filter((p) => p.price_usd_per_mt !== null)
    .map((p) => ({ ...p, date: p.date?.slice(5) }));

  const volumeSeries = data.volume_summary.daily_series
    .filter((d) => d.daily_volume_mt > 0)
    .map((d) => ({ ...d, date: d.date.slice(5) }));

  const fviValue = fvi?.fvi_adjusted ?? fvi?.fvi_raw;
  const fviSignal = fvi?.signal_adjusted ?? fvi?.signal;

  return (
    <div className="p-6 max-w-6xl">
      <button onClick={() => navigate('/commodities')}
        className="flex items-center gap-1 text-xs mb-4 hover:underline"
        style={{ color: 'var(--accent-cyan)' }}>
        <ArrowLeft className="w-3 h-3" /> Back to commodities
      </button>

      <PageHeader
        title={data.commodity.hct_name}
        subtitle={`${data.commodity.hct_group} | ${data.volume_summary.record_count.toLocaleString()} records`}
      />

      {/* Key metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard
          label="Implied FOB"
          value={ipc?.price_usd_per_mt ? `$${ipc.price_usd_per_mt.toLocaleString()}` : null}
          sub={ipc?.confidence ? `${ipc.confidence} confidence` : undefined}
          accent="cyan"
        />
        <MetricCard
          label="Flow Velocity"
          value={fviValue != null ? fviValue.toFixed(2) : null}
          sub={fviSignal?.replace(/_/g, ' ').toLowerCase()}
          accent={fviValue && fviValue > 1.1 ? 'green' : fviValue && fviValue < 0.9 ? 'red' : 'amber'}
        />
        <MetricCard
          label="Total Volume"
          value={`${(data.volume_summary.total_volume_mt / 1000).toFixed(1)}K`}
          sub="MT in period"
          accent="blue"
        />
        <MetricCard
          label="Avg Price"
          value={data.volume_summary.avg_price_per_mt
            ? `$${data.volume_summary.avg_price_per_mt.toLocaleString()}`
            : null}
          sub="USD/MT"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* IPC Price Chart */}
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Implied Price Curve (FOB USD/MT)
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

        {/* Volume Chart */}
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Daily Shipment Volumes (MT)
          </div>
          {volumeSeries.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={volumeSeries}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }}
                />
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

      {/* Origin & Counterparty row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Origin breakdown */}
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Origin Breakdown
          </div>
          {data.volume_summary.country_breakdown.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie
                    data={data.volume_summary.country_breakdown}
                    dataKey="volume_mt"
                    nameKey="country"
                    cx="50%" cy="50%"
                    innerRadius={40} outerRadius={65}
                    paddingAngle={2}
                  >
                    {data.volume_summary.country_breakdown.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1 mt-2">
                {data.volume_summary.country_breakdown.slice(0, 6).map((c, i) => (
                  <div key={c.country} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      <span style={{ color: 'var(--text-secondary)' }}>{c.country}</span>
                    </div>
                    <span className="tabular-nums" style={{ color: 'var(--text-primary)' }}>
                      {c.share_pct}%
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-sm" style={{ color: 'var(--text-muted)' }}>No data</div>
          )}
        </Card>

        {/* Top Buyers */}
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Top Buyers
            {data.top_buyers.concentration && (
              <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded"
                style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                HHI: {data.top_buyers.hhi?.toFixed(3)} ({data.top_buyers.concentration})
              </span>
            )}
          </div>
          <div className="space-y-2">
            {data.top_buyers.top_entities?.slice(0, 8).map((e) => (
              <div key={e.entity} className="flex items-center justify-between text-xs">
                <span className="truncate mr-2" style={{ color: 'var(--text-secondary)' }}>
                  {e.entity}
                </span>
                <div className="flex items-center gap-2 flex-shrink-0 tabular-nums">
                  <span style={{ color: 'var(--text-primary)' }}>{e.market_share_pct}%</span>
                  <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                    <div className="h-full rounded-full" style={{
                      width: `${Math.min(e.market_share_pct, 100)}%`, background: 'var(--accent-cyan)'
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Top Sellers */}
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Top Sellers
          </div>
          <div className="space-y-2">
            {data.top_sellers.top_entities?.slice(0, 8).map((e) => (
              <div key={e.entity} className="flex items-center justify-between text-xs">
                <span className="truncate mr-2" style={{ color: 'var(--text-secondary)' }}>
                  {e.entity}
                </span>
                <div className="flex items-center gap-2 flex-shrink-0 tabular-nums">
                  <span style={{ color: 'var(--text-primary)' }}>{e.market_share_pct}%</span>
                  <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                    <div className="h-full rounded-full" style={{
                      width: `${Math.min(e.market_share_pct, 100)}%`, background: 'var(--accent-blue)'
                    }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
