import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Signal } from '../api/client';
import { Card, SeverityBadge, LoadingSpinner, EmptyState, PageHeader } from '../components/Cards';
import { AlertTriangle, TrendingDown, TrendingUp, UserPlus, Zap } from 'lucide-react';

const SIGNAL_ICONS: Record<string, typeof Zap> = {
  FLOW_VELOCITY: Zap,
  SD_DELTA: TrendingUp,
  PRICE_MOVEMENT: TrendingDown,
  COUNTERPARTY_NEW_ENTRANT: UserPlus,
  COUNTERPARTY_WITHDRAWAL: AlertTriangle,
  COUNTERPARTY_VOLUME_SURGE: TrendingUp,
};

export default function SignalFeed() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSignals(50)
      .then((data) => setSignals(data.signals))
      .catch(() => setSignals([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><LoadingSpinner /></div>;

  return (
    <div className="p-6 max-w-4xl">
      <PageHeader
        title="Trading Signals"
        subtitle="Anomalies, flow changes, and price movements across all monitored corridors"
      />

      {signals.length === 0 ? (
        <EmptyState message="No active signals. Markets are quiet — or you need to pull data first." />
      ) : (
        <div className="space-y-3">
          {signals.map((sig, i) => {
            const Icon = SIGNAL_ICONS[sig.signal_type] || Zap;
            return (
              <Card key={i} className="hover:border-cyan-800 transition-colors cursor-default">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">
                    <Icon className="w-4 h-4" style={{
                      color: sig.severity === 'HIGH' ? 'var(--accent-red)'
                        : sig.severity === 'MEDIUM' ? 'var(--accent-amber)'
                        : 'var(--accent-green)'
                    }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge severity={sig.severity} />
                      <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                        {sig.signal_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                      {sig.headline}
                    </div>
                    {sig.detail?.implication != null && (
                      <div className="text-xs mt-1.5" style={{ color: 'var(--text-secondary)' }}>
                        {sig.detail.implication as string}
                      </div>
                    )}
                  </div>
                  {sig.timestamp && (
                    <div className="text-[10px] flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
                      {sig.timestamp}
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
