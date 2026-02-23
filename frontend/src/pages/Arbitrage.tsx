import { useEffect, useState } from 'react';
import { api, CommodityListItem, ArbOpportunity } from '../api/client';
import { Card, ConfidenceBadge, LoadingSpinner, EmptyState, PageHeader } from '../components/Cards';
import { ArrowRight } from 'lucide-react';

export default function Arbitrage() {
  const [commodities, setCommodities] = useState<CommodityListItem[]>([]);
  const [selectedCommodity, setSelectedCommodity] = useState<string>('');
  const [opportunities, setOpportunities] = useState<ArbOpportunity[]>([]);
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
    api.arbitrageScan(selectedCommodity)
      .then((d) => setOpportunities(d.opportunities))
      .catch(() => setOpportunities([]))
      .finally(() => setLoading(false));
  }, [selectedCommodity]);

  return (
    <div className="p-6 max-w-5xl">
      <PageHeader
        title="Arbitrage Scanner"
        subtitle="Cross-origin price differentials that may represent trading opportunities"
      />

      <div className="mb-6">
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
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : opportunities.length === 0 ? (
        <EmptyState message="No arbitrage opportunities detected — or insufficient data to compare origins." />
      ) : (
        <div className="space-y-3">
          {opportunities.map((arb, i) => {
            const spreadColor = arb.spread_pct > 10 ? 'var(--accent-red)'
              : arb.spread_pct > 5 ? 'var(--accent-amber)'
              : 'var(--accent-green)';

            return (
              <Card key={i} className="hover:border-cyan-800 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {/* Cheaper origin */}
                    <div>
                      <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                        Cheaper
                      </div>
                      <div className="text-sm font-medium" style={{ color: 'var(--accent-green)' }}>
                        {arb.cheaper_origin}
                      </div>
                      <div className="text-lg font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                        ${arb.cheaper_fob.toLocaleString()}
                      </div>
                      <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>FOB USD/MT</div>
                    </div>

                    <ArrowRight className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />

                    {/* More expensive origin */}
                    <div>
                      <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                        More Expensive
                      </div>
                      <div className="text-sm font-medium" style={{ color: 'var(--accent-red)' }}>
                        {arb.expensive_origin}
                      </div>
                      <div className="text-lg font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                        ${arb.expensive_fob.toLocaleString()}
                      </div>
                      <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>FOB USD/MT</div>
                    </div>
                  </div>

                  {/* Spread */}
                  <div className="text-right">
                    <div className="text-2xl font-bold tabular-nums" style={{ color: spreadColor }}>
                      {arb.spread_pct.toFixed(1)}%
                    </div>
                    <div className="text-sm tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      ${arb.spread_usd}/MT spread
                    </div>
                    <div className="mt-1">
                      <ConfidenceBadge confidence={arb.confidence} />
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
