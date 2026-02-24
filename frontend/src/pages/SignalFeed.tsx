import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Signal } from '../api/client';
import { Card, SeverityBadge, PageHeader } from '../components/Cards';
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
  const [recordCount, setRecordCount] = useState(0);
  const [commodityCount, setCommodityCount] = useState(0);

  useEffect(() => {
    // Fetch signals immediately — no loading bar, just show what we have
    Promise.all([
      api.getSignals(50).catch(() => ({ signals: [], total: 0 })),
      api.harvestStatus().catch(() => null),
    ]).then(([sigData, status]) => {
      setSignals(sigData.signals);
      if (status) {
        setRecordCount(status.total_records);
        setCommodityCount(status.commodities_loaded);
      }
      setLoading(false);
    });

    // Poll for updates every 15s (data arrives in background)
    const interval = setInterval(() => {
      api.getSignals(50)
        .then((d) => setSignals(d.signals))
        .catch(() => {});
      api.harvestStatus()
        .then((s) => { setRecordCount(s.total_records); setCommodityCount(s.commodities_loaded); })
        .catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-6 max-w-4xl">
      <PageHeader
        title="Trading Signals"
        subtitle="Anomalies, flow changes, and price movements across all monitored corridors"
      />

      {loading ? (
        <Card>
          <div className="text-center py-10">
            <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Connecting to intelligence engine...
            </div>
          </div>
        </Card>
      ) : signals.length === 0 ? (
        <Card>
          <div className="text-center py-10">
            <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              No active signals detected. Markets are quiet across all monitored corridors.
            </div>
            <div className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
              {recordCount > 0
                ? `${recordCount.toLocaleString()} records analyzed across ${commodityCount} commodities`
                : 'Trade data is loading in the background. Signals will appear as analysis completes.'}
            </div>
          </div>
        </Card>
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
