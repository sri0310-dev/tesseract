import { useEffect, useState } from 'react';
import { api, CorridorListItem, CorridorCompareResult } from '../api/client';
import { Card, ConfidenceBadge, LoadingSpinner, EmptyState, PageHeader, MetricCard } from '../components/Cards';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function Corridors() {
  const [corridors, setCorridors] = useState<CorridorListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [comparison, setComparison] = useState<CorridorCompareResult | null>(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    api.listCorridors()
      .then((d) => setCorridors(d.corridors))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleCompare = async (corridor: CorridorListItem) => {
    setSelected(corridor.id);
    setComparing(true);
    try {
      const destPort = corridor.destinations?.[0]
        ? `TUTICORIN` // Default for India destinations
        : '';
      const origins = corridor.origins.map((c) => ({
        country: c,
        port: c === 'IVORY COAST' ? 'ABIDJAN'
          : c === 'GHANA' ? 'TEMA'
          : c === 'NIGERIA' ? 'LAGOS'
          : c === 'TANZANIA' ? 'DAR ES SALAAM'
          : c === 'ETHIOPIA' ? 'DJIBOUTI'
          : c,
      }));
      const result = await api.compareCorridors({
        hct_id: corridor.commodity,
        origins,
        dest_port: destPort,
      });
      setComparison(result);
    } catch {
      setComparison(null);
    } finally {
      setComparing(false);
    }
  };

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;

  const comparisonChartData = comparison?.comparisons
    .filter((c) => c.implied_cif_usd_per_mt != null)
    .map((c) => ({
      origin: c.origin,
      FOB: c.fob_usd_per_mt,
      Freight: c.freight_usd_per_mt,
      Insurance: c.insurance_usd_per_mt,
      'Port Charges': c.port_charges_usd_per_mt,
    }));

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title="Corridor Explorer"
        subtitle="Compare origins, compute delivered costs, and find the cheapest supply route"
      />

      {corridors.length === 0 ? (
        <EmptyState message="No corridors configured." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {corridors.map((c) => (
            <Card key={c.id} className={`cursor-pointer transition-colors ${
              selected === c.id ? 'border-cyan-600' : 'hover:border-cyan-800'
            }`}>
              <div onClick={() => handleCompare(c)}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                    {c.name}
                  </span>
                  <ConfidenceBadge confidence={c.price_confidence} />
                </div>
                <div className="text-xl font-semibold tabular-nums" style={{
                  color: c.current_fob ? 'var(--accent-cyan)' : 'var(--text-muted)'
                }}>
                  {c.current_fob ? `$${c.current_fob.toLocaleString()}/MT FOB` : 'No price data'}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {c.origins.map((o) => (
                    <span key={o} className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                      {o}
                    </span>
                  ))}
                  <span className="text-[10px] px-1 py-0.5" style={{ color: 'var(--text-muted)' }}>→</span>
                  {c.destinations.map((d) => (
                    <span key={d} className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(6,182,212,0.1)', color: 'var(--accent-cyan)' }}>
                      {d}
                    </span>
                  ))}
                </div>
                <div className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                  {c.record_count.toLocaleString()} records
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Comparison Results */}
      {comparing && <LoadingSpinner />}
      {comparison && !comparing && (
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: 'var(--text-muted)' }}>
            Origin Comparison → {comparison.destination_port}
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <MetricCard
              label="Cheapest Origin"
              value={comparison.cheapest_origin ?? '---'}
              accent="green"
            />
            <MetricCard
              label="Origin Spread"
              value={comparison.origin_spread_usd != null ? `$${comparison.origin_spread_usd}` : null}
              sub="USD/MT between cheapest and most expensive"
              accent="amber"
            />
            <MetricCard
              label="Origins with Data"
              value={comparison.n_origins_with_data}
              accent="blue"
            />
          </div>

          {/* Stacked cost chart */}
          {comparisonChartData && comparisonChartData.length > 0 && (
            <Card className="mb-4">
              <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
                Delivered Cost Breakdown (USD/MT)
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={comparisonChartData} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <YAxis dataKey="origin" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} width={100} />
                  <Tooltip contentStyle={{ background: '#1a2236', border: '1px solid #2a3654', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="FOB" stackId="a" fill="#06b6d4" name="FOB" />
                  <Bar dataKey="Freight" stackId="a" fill="#3b82f6" name="Freight" />
                  <Bar dataKey="Insurance" stackId="a" fill="#8b5cf6" name="Insurance" />
                  <Bar dataKey="Port Charges" stackId="a" fill="#f59e0b" name="Port Charges" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Detail table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr style={{ color: 'var(--text-muted)' }}>
                    <th className="text-left py-2 px-2">Origin</th>
                    <th className="text-right py-2 px-2">FOB</th>
                    <th className="text-right py-2 px-2">Freight</th>
                    <th className="text-right py-2 px-2">Insurance</th>
                    <th className="text-right py-2 px-2">Port</th>
                    <th className="text-right py-2 px-2 font-semibold">CIF</th>
                    <th className="text-center py-2 px-2">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.comparisons.map((c) => (
                    <tr key={c.origin} className="border-t" style={{ borderColor: 'var(--border)' }}>
                      <td className="py-2 px-2" style={{ color: 'var(--text-primary)' }}>{c.origin}</td>
                      <td className="text-right py-2 px-2 tabular-nums">{c.fob_usd_per_mt ?? '---'}</td>
                      <td className="text-right py-2 px-2 tabular-nums">{c.freight_usd_per_mt ?? '---'}</td>
                      <td className="text-right py-2 px-2 tabular-nums">{c.insurance_usd_per_mt?.toFixed(2) ?? '---'}</td>
                      <td className="text-right py-2 px-2 tabular-nums">{c.port_charges_usd_per_mt ?? '---'}</td>
                      <td className="text-right py-2 px-2 tabular-nums font-semibold" style={{
                        color: c.implied_cif_usd_per_mt ? 'var(--accent-cyan)' : 'var(--text-muted)'
                      }}>
                        {c.implied_cif_usd_per_mt ? `$${c.implied_cif_usd_per_mt.toLocaleString()}` : '---'}
                      </td>
                      <td className="text-center py-2 px-2"><ConfidenceBadge confidence={c.ipc_confidence} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
