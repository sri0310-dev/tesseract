import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { CommodityListItem, MarketShareResult, Anomaly } from '../api/client';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { Card, SeverityBadge, LoadingSpinner, EmptyState, PageHeader, MetricCard } from '../components/Cards';

export default function Counterparty() {
  const [commodities, setCommodities] = useState<CommodityListItem[]>([]);
  const [selectedCommodity, setSelectedCommodity] = useState<string>('');
  const [partyType, setPartyType] = useState<'consignee' | 'consignor'>('consignee');
  const [shares, setShares] = useState<MarketShareResult | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.listCommodities().then((d) => {
      setCommodities(d.commodities);
      if (d.commodities.length > 0) {
        setSelectedCommodity(d.commodities[0].hct_id);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedCommodity) return;
    setLoading(true);

    Promise.all([
      api.marketShares({ hct_id: selectedCommodity, party_type: partyType, top_n: 20 }),
      api.counterpartyAnomalies({ hct_id: selectedCommodity, party_type: partyType }),
    ])
      .then(([s, a]) => {
        setShares(s);
        setAnomalies(a.anomalies);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedCommodity, partyType]);

  const chartData = shares?.top_entities.slice(0, 12).map((e) => ({
    name: e.entity.length > 18 ? e.entity.slice(0, 18) + '...' : e.entity,
    volume: e.volume_mt,
    share: e.market_share_pct,
  }));

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title="Counterparty Intelligence"
        subtitle="Who is buying, who is selling, and what changed"
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select
          value={selectedCommodity}
          onChange={(e) => setSelectedCommodity(e.target.value)}
          className="text-sm rounded-md px-3 py-1.5 border outline-none"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
        >
          {commodities.map((c) => (
            <option key={c.hct_id} value={c.hct_id}>{c.hct_name}</option>
          ))}
        </select>

        <div className="flex rounded-md overflow-hidden border" style={{ borderColor: 'var(--border)' }}>
          {(['consignee', 'consignor'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setPartyType(t)}
              className="text-xs px-3 py-1.5 transition-colors"
              style={{
                background: partyType === t ? 'var(--accent-cyan)' : 'var(--bg-card)',
                color: partyType === t ? '#000' : 'var(--text-secondary)',
              }}
            >
              {t === 'consignee' ? 'Buyers' : 'Sellers'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : shares && shares.top_entities.length > 0 ? (
        <>
          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <MetricCard label="Total Volume" value={`${(shares.total_volume_mt / 1000).toFixed(1)}K MT`} accent="cyan" />
            <MetricCard label="Unique Entities" value={shares.unique_entities} accent="blue" />
            <MetricCard
              label="Concentration (HHI)"
              value={shares.hhi?.toFixed(3)}
              sub={shares.concentration}
              accent={shares.concentration === 'HIGH' ? 'red' : shares.concentration === 'MODERATE' ? 'amber' : 'green'}
            />
            <MetricCard
              label="Top Entity Share"
              value={shares.top_entities[0] ? `${shares.top_entities[0].market_share_pct}%` : '---'}
              sub={shares.top_entities[0]?.entity}
            />
          </div>

          {/* Bar chart */}
          {chartData && chartData.length > 0 && (
            <Card className="mb-6">
              <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                Market Share by Volume
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: '#94a3b8' }} width={140} />
                  <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="volume" fill="#06b6d4" radius={[0, 4, 4, 0]} name="Volume (MT)" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Entity table */}
          <Card className="mb-6">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ color: 'var(--text-muted)' }}>
                    <th className="text-left py-2 px-2">Entity</th>
                    <th className="text-right py-2 px-2">Volume (MT)</th>
                    <th className="text-right py-2 px-2">Value (USD)</th>
                    <th className="text-right py-2 px-2">Shipments</th>
                    <th className="text-right py-2 px-2">Share %</th>
                    <th className="text-right py-2 px-2">Avg $/MT</th>
                  </tr>
                </thead>
                <tbody>
                  {shares.top_entities.map((e) => (
                    <tr key={e.entity} className="border-t" style={{ borderColor: 'var(--border)' }}>
                      <td className="py-2 px-2 font-medium" style={{ color: 'var(--text-primary)' }}>
                        {e.entity}
                      </td>
                      <td className="text-right py-2 px-2 tabular-nums">{e.volume_mt.toLocaleString()}</td>
                      <td className="text-right py-2 px-2 tabular-nums">${e.value_usd.toLocaleString()}</td>
                      <td className="text-right py-2 px-2 tabular-nums">{e.shipments}</td>
                      <td className="text-right py-2 px-2 tabular-nums font-semibold" style={{ color: 'var(--accent-cyan)' }}>
                        {e.market_share_pct}%
                      </td>
                      <td className="text-right py-2 px-2 tabular-nums">
                        {e.avg_price_per_mt ? `$${e.avg_price_per_mt.toLocaleString()}` : '---'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Anomalies */}
          {anomalies.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                Counterparty Anomalies
              </h2>
              <div className="space-y-2">
                {anomalies.map((a, i) => (
                  <Card key={i}>
                    <div className="flex items-start gap-3">
                      <SeverityBadge severity={a.severity} />
                      <div>
                        <span className="text-[10px] uppercase tracking-wider mr-2" style={{ color: 'var(--text-muted)' }}>
                          {a.type.replace(/_/g, ' ')}
                        </span>
                        <div className="text-sm mt-1" style={{ color: 'var(--text-primary)' }}>
                          {a.detail}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <EmptyState message="No counterparty data available for this commodity." />
      )}
    </div>
  );
}
