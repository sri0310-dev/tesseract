import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { ArrivalsResult, DeepDiveResult, ImporterRow as ImporterRowType } from '../api/client';
import { Card, LoadingSpinner, PageHeader } from '../components/Cards';
import {
  ArrowLeft, ChevronRight, TrendingUp, TrendingDown, Minus,
  ArrowUpRight, ArrowDownRight, Anchor, Ship,
} from 'lucide-react';

const MOMENTUM_ICONS: Record<string, { color: string; icon: typeof TrendingUp; label: string }> = {
  SURGING:     { color: 'var(--accent-red)',       icon: ArrowUpRight,  label: 'Surging' },
  PICKING_UP:  { color: 'var(--accent-green)',     icon: TrendingUp,    label: 'Picking Up' },
  STEADY:      { color: 'var(--text-secondary)',   icon: Minus,         label: 'Steady' },
  SLOWING:     { color: 'var(--accent-amber)',     icon: TrendingDown,  label: 'Slowing' },
  DROPPING:    { color: 'var(--accent-red)',        icon: ArrowDownRight, label: 'Dropping' },
  NEW:         { color: 'var(--accent-cyan)',       icon: ArrowUpRight,  label: 'New' },
  NO_DATA:     { color: 'var(--text-muted)',       icon: Minus,         label: 'No Data' },
};

function fmt(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}K` : n.toFixed(0);
}

function formatDate(iso: string) {
  if (!iso) return '';
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function CommodityDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [arrivals, setArrivals] = useState<ArrivalsResult | null>(null);
  const [deepDive, setDeepDive] = useState<DeepDiveResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const end = new Date().toISOString().slice(0, 10);
    const start = new Date(Date.now() - 30 * 86400000).toISOString().slice(0, 10);

    Promise.all([
      api.commodityArrivals({ hct_id: id, start_date: start, end_date: end }).catch(() => null),
      api.commodityDeepDive({ hct_id: id, start_date: start, end_date: end }).catch(() => null),
    ]).then(([arr, dd]) => {
      setArrivals(arr);
      setDeepDive(dd);
      setLoading(false);
    });
  }, [id]);

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;
  if (!arrivals && !deepDive) return <div className="p-6" style={{ color: 'var(--text-muted)' }}>No data available</div>;

  const commodityName = arrivals?.commodity.hct_name || deepDive?.commodity.hct_name || id || '';

  return (
    <div className="p-6 max-w-7xl">
      <button onClick={() => navigate('/commodities')}
        className="flex items-center gap-1 text-xs mb-4 hover:underline"
        style={{ color: 'var(--accent-cyan)' }}>
        <ArrowLeft className="w-3 h-3" /> Back to commodities
      </button>

      <PageHeader
        title={commodityName}
        subtitle={arrivals ? `As of ${formatDate(arrivals.as_of)}` : undefined}
      />

      {/* ── Section 1: Arrivals Summary (Origin x Outturn x Volume) ── */}
      {arrivals && arrivals.arrivals_summary.length > 0 && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                Arrivals Summary
              </div>
              <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                Origin x Outturn x Volume | as of {formatDate(arrivals.as_of)}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-3 font-medium">Origin</th>
                  <th className="text-left py-2 pr-3 font-medium">Outturn</th>
                  <th className="text-left py-2 pr-3 font-medium">Nut Count</th>
                  <th className="text-right py-2 pr-3 font-medium">Last 7d (MT)</th>
                  <th className="text-right py-2 pr-3 font-medium">Last 14d (MT)</th>
                  <th className="text-right py-2 pr-3 font-medium">Last 30d (MT)</th>
                  <th className="text-right py-2 pr-3 font-medium">Shipments</th>
                  <th className="text-right py-2 font-medium">FOB $/MT</th>
                </tr>
              </thead>
              <tbody>
                {arrivals.arrivals_summary.map((row, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-2.5 pr-3 font-medium" style={{ color: 'var(--text-primary)' }}>
                      {row.origin}
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{
                          background: row.outturn === 'Unknown' ? 'var(--bg-secondary)' : 'rgba(6, 182, 212, 0.15)',
                          color: row.outturn === 'Unknown' ? 'var(--text-muted)' : 'var(--accent-cyan)',
                        }}>
                        {row.outturn}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3" style={{ color: 'var(--text-muted)' }}>
                      {row.nut_count}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums font-medium" style={{ color: 'var(--text-primary)' }}>
                      {fmt(row.last_7d_mt)}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {fmt(row.last_14d_mt)}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {fmt(row.last_30d_mt)}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      {row.shipments_30d}
                    </td>
                    <td className="py-2.5 text-right tabular-nums font-medium"
                      style={{ color: row.avg_fob_usd_per_mt ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                      {row.avg_fob_usd_per_mt ? `$${row.avg_fob_usd_per_mt.toLocaleString()}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
              {/* Totals row */}
              <tfoot>
                <tr className="border-t-2" style={{ borderColor: 'var(--border)' }}>
                  <td className="py-2.5 pr-3 font-semibold" colSpan={3} style={{ color: 'var(--text-primary)' }}>
                    Total
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {fmt(arrivals.arrivals_summary.reduce((s, r) => s + r.last_7d_mt, 0))}
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {fmt(arrivals.arrivals_summary.reduce((s, r) => s + r.last_14d_mt, 0))}
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {fmt(arrivals.arrivals_summary.reduce((s, r) => s + r.last_30d_mt, 0))}
                  </td>
                  <td className="py-2.5 pr-3 text-right tabular-nums font-semibold" style={{ color: 'var(--text-primary)' }}>
                    {arrivals.arrivals_summary.reduce((s, r) => s + r.shipments_30d, 0)}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        </Card>
      )}

      {/* ── Section 2: Origin Momentum ────────────────────────── */}
      {arrivals && arrivals.origin_momentum.length > 0 && (
        <Card className="mb-6">
          <div className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: 'var(--text-muted)' }}>
            <Ship className="w-3.5 h-3.5 inline mr-1.5" />
            Origin Momentum (week-over-week)
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {arrivals.origin_momentum.map((om) => {
              const cfg = MOMENTUM_ICONS[om.signal] || MOMENTUM_ICONS.NO_DATA;
              const Icon = cfg.icon;
              return (
                <div key={om.origin} className="rounded-lg p-3" style={{ background: 'var(--bg-secondary)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {om.origin}
                    </span>
                    <div className="flex items-center gap-1">
                      <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
                      <span className="text-[10px] font-medium" style={{ color: cfg.color }}>
                        {cfg.label}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-lg font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                      {fmt(om.last_7d_mt)} MT
                    </span>
                    {om.change_pct !== null && (
                      <span className="text-xs font-medium tabular-nums" style={{ color: cfg.color }}>
                        {om.change_pct > 0 ? '+' : ''}{om.change_pct}%
                      </span>
                    )}
                  </div>

                  <div className="text-[10px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
                    Prior week: {fmt(om.prior_7d_mt)} MT · {om.last_7d_shipments} shipments
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* ── Section 3: Port Arrivals ──────────────────────────── */}
      {arrivals && arrivals.port_arrivals.length > 0 && (
        <Card className="mb-6">
          <div className="text-xs font-semibold uppercase tracking-wider mb-4" style={{ color: 'var(--text-muted)' }}>
            <Anchor className="w-3.5 h-3.5 inline mr-1.5" />
            Port Arrivals
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 pr-3 font-medium">Port</th>
                  <th className="text-right py-2 pr-3 font-medium">Last 7d (MT)</th>
                  <th className="text-right py-2 pr-3 font-medium">Last 14d (MT)</th>
                  <th className="text-right py-2 pr-3 font-medium">Last 30d (MT)</th>
                  <th className="text-right py-2 pr-3 font-medium">Shipments</th>
                  <th className="text-left py-2 font-medium">Top Origins</th>
                </tr>
              </thead>
              <tbody>
                {arrivals.port_arrivals.map((p, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-2.5 pr-3 font-medium" style={{ color: 'var(--text-primary)' }}>
                      {p.port}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums font-medium" style={{ color: 'var(--text-primary)' }}>
                      {fmt(p.last_7d_mt)}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {fmt(p.last_14d_mt)}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {fmt(p.last_30d_mt)}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      {p.shipments_30d}
                    </td>
                    <td className="py-2.5" style={{ color: 'var(--text-muted)' }}>
                      {p.top_origins.join(', ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── Section 4: Top Importers (last 4 weeks) ──────────── */}
      {arrivals && arrivals.top_importers.length > 0 && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Top Importers — Last 30 Days
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Click any name to see full profile
            </div>
          </div>

          <div className="space-y-2">
            {arrivals.top_importers.slice(0, 12).map((imp) => (
              <ImporterRow
                key={imp.entity}
                importer={imp}
                onNavigate={(name) => {
                  const params = new URLSearchParams({ name, trade_type: 'IMPORT' });
                  navigate(`/counterparty-search?${params.toString()}`);
                }}
              />
            ))}
          </div>
        </Card>
      )}

      {/* ── Section 5: Price by Grade x Origin (from deep-dive) ── */}
      {deepDive && deepDive.price_by_grade.length > 0 && (
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Price by Quality & Origin
            </div>
            <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              FOB USD/MT | {formatDate(deepDive.period.start)} – {formatDate(deepDive.period.end)}
            </div>
          </div>

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
                {deepDive.price_by_grade.map((row, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-2.5 pr-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{ background: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-cyan)' }}>
                        {row.grade}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3" style={{ color: 'var(--text-secondary)' }}>{row.origin}</td>
                    <td className="py-2.5 pr-3 text-right tabular-nums font-medium"
                      style={{ color: row.fob_usd_per_mt ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                      {row.fob_usd_per_mt ? `$${row.fob_usd_per_mt.toLocaleString()}` : '—'}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-muted)' }}>
                      {row.price_range ? `$${row.price_range.min.toLocaleString()} – $${row.price_range.max.toLocaleString()}` : '—'}
                    </td>
                    <td className="py-2.5 pr-3 text-right tabular-nums" style={{ color: 'var(--text-primary)' }}>
                      {fmt(row.volume_mt)}
                    </td>
                    <td className="py-2.5 text-right tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {row.shipments}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── No data state ─────────────────────────────────────── */}
      {!arrivals && !deepDive && (
        <Card>
          <div className="text-sm text-center py-8" style={{ color: 'var(--text-muted)' }}>
            No trade data available for this commodity yet. Data will load automatically.
          </div>
        </Card>
      )}
    </div>
  );
}


/* ── Importer Row Component ──────────────────────────────────────── */

function ImporterRow({
  importer: imp,
  onNavigate,
}: {
  importer: ImporterRowType;
  onNavigate: (name: string) => void;
}) {
  return (
    <div
      className="group rounded-md p-3 cursor-pointer transition-colors hover:bg-white/5 border"
      style={{ borderColor: 'var(--border)' }}
      onClick={() => onNavigate(imp.entity)}
    >
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium truncate max-w-[240px]" style={{ color: 'var(--text-primary)' }}>
            {imp.entity}
          </span>
          <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ color: 'var(--accent-cyan)' }} />
        </div>
        <div className="flex items-center gap-3 text-xs tabular-nums">
          <span style={{ color: 'var(--accent-cyan)' }}>
            {imp.avg_price_per_mt ? `$${imp.avg_price_per_mt.toLocaleString()}/MT` : '—'}
          </span>
          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
            {fmt(imp.volume_mt)} MT
          </span>
          <span style={{ color: 'var(--text-muted)' }}>
            {imp.market_share_pct}%
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap text-[10px]">
        <span style={{ color: 'var(--text-muted)' }}>
          {imp.shipments} shipments
        </span>

        {/* Outturn badges */}
        {imp.top_outturns.length > 0 && (
          <>
            <span style={{ color: 'var(--text-muted)' }}>·</span>
            {imp.top_outturns.map(o => (
              <span key={o.outturn} className="px-1.5 py-0.5 rounded"
                style={{ background: 'rgba(6, 182, 212, 0.15)', color: 'var(--accent-cyan)' }}>
                {o.outturn} ({fmt(o.volume_mt)} MT)
              </span>
            ))}
          </>
        )}

        {/* Origin badges */}
        {imp.top_origins.length > 0 && (
          <>
            <span style={{ color: 'var(--text-muted)' }}>·</span>
            {imp.top_origins.map(o => (
              <span key={o.country} style={{ color: 'var(--text-muted)' }}>
                {o.country}
              </span>
            ))}
          </>
        )}

        {/* Port badges */}
        {imp.top_ports.length > 0 && (
          <>
            <span style={{ color: 'var(--text-muted)' }}>·</span>
            <span style={{ color: 'var(--text-muted)' }}>
              via {imp.top_ports.join(', ')}
            </span>
          </>
        )}
      </div>

      {/* Market share bar */}
      <div className="mt-2 h-1 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
        <div className="h-full rounded-full transition-all" style={{
          width: `${Math.min(imp.market_share_pct, 100)}%`,
          background: 'var(--accent-cyan)',
        }} />
      </div>
    </div>
  );
}
