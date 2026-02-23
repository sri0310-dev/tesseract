import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { CommodityListItem } from '../api/client';
import { Card, ConfidenceBadge, LoadingSpinner, EmptyState, PageHeader } from '../components/Cards';

export default function Commodities() {
  const [commodities, setCommodities] = useState<CommodityListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.listCommodities()
      .then((d) => setCommodities(d.commodities))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;

  const groups = new Map<string, CommodityListItem[]>();
  commodities.forEach((c) => {
    const arr = groups.get(c.hct_supergroup) || [];
    arr.push(c);
    groups.set(c.hct_supergroup, arr);
  });

  return (
    <div className="p-6 max-w-5xl">
      <PageHeader
        title="Commodity Dashboard"
        subtitle="Implied prices, confidence levels, and record counts for all tracked commodities"
      />

      {commodities.length === 0 ? (
        <EmptyState message="No commodities tracked yet." />
      ) : (
        <div className="space-y-6">
          {Array.from(groups.entries()).map(([group, items]) => (
            <div key={group}>
              <h2 className="text-xs font-semibold uppercase tracking-widest mb-3"
                style={{ color: 'var(--text-muted)' }}>
                {group}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((c) => (
                  <Card
                    key={c.hct_id}
                    className="hover:border-cyan-800 transition-colors cursor-pointer"
                  >
                    <div onClick={() => navigate(`/commodities/${encodeURIComponent(c.hct_id)}`)}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                          {c.hct_name}
                        </span>
                        <ConfidenceBadge confidence={c.price_confidence} />
                      </div>
                      <div className="text-2xl font-semibold tabular-nums" style={{
                        color: c.current_price_usd ? 'var(--accent-cyan)' : 'var(--text-muted)'
                      }}>
                        {c.current_price_usd ? `$${c.current_price_usd.toLocaleString()}` : '---'}
                        <span className="text-xs font-normal ml-1" style={{ color: 'var(--text-muted)' }}>
                          /MT
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                        <span>{c.record_count.toLocaleString()} records</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{ background: 'var(--bg-secondary)' }}>
                          {c.hct_group}
                        </span>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
