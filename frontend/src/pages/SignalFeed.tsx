import { useEffect, useState, useCallback } from 'react';
import { api } from '../api/client';
import type { Signal, HarvestStatus } from '../api/client';
import { Card, SeverityBadge, PageHeader } from '../components/Cards';
import { AlertTriangle, TrendingDown, TrendingUp, UserPlus, Zap, RefreshCw } from 'lucide-react';

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
  const [status, setStatus] = useState<HarvestStatus | null>(null);
  const [polling, setPolling] = useState(true);

  const fetchSignals = useCallback(() => {
    api.getSignals(50)
      .then((data) => setSignals(data.signals))
      .catch(() => {});
  }, []);

  // Poll harvest status until data arrives
  useEffect(() => {
    if (!polling) return;

    const check = async () => {
      try {
        const s = await api.harvestStatus();
        setStatus(s);
        if (s.loading_complete) {
          setPolling(false);
          fetchSignals();
          setLoading(false);
        }
      } catch {
        // Backend not ready yet, keep polling
      }
    };

    check();
    const interval = setInterval(check, 3000);
    return () => clearInterval(interval);
  }, [polling, fetchSignals]);

  // Also fetch signals on mount (in case data is already loaded)
  useEffect(() => {
    api.getSignals(50)
      .then((data) => {
        setSignals(data.signals);
        setLoading(false);
        if (data.signals.length > 0) setPolling(false);
      })
      .catch(() => {});
  }, []);

  if (loading && !status?.loading_complete) {
    return (
      <div className="p-6 max-w-4xl">
        <PageHeader
          title="Trading Signals"
          subtitle="Anomalies, flow changes, and price movements across all monitored corridors"
        />
        <Card>
          <div className="flex items-center gap-3 mb-4">
            <RefreshCw className="w-5 h-5 animate-spin" style={{ color: 'var(--accent-cyan)' }} />
            <div>
              <div className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                Loading commodity data from Eximpedia...
              </div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                First load pulls trade data for all priority commodities. This takes a moment.
              </div>
            </div>
          </div>
          {status && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-secondary)' }}>
                <span>{status.total_records.toLocaleString()} records loaded</span>
                <span>{status.commodities_loaded}/{status.total_commodities} commodities</span>
              </div>
              <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-secondary)' }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.max(5, (status.commodities_loaded / Math.max(status.total_commodities, 1)) * 100)}%`,
                    background: 'var(--accent-cyan)',
                  }}
                />
              </div>
              {Object.entries(status.per_commodity).length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {Object.entries(status.per_commodity).map(([, info]) => (
                    <span key={info.name} className="text-[10px] px-2 py-0.5 rounded" style={{
                      background: 'rgba(6,182,212,0.1)', color: 'var(--accent-cyan)',
                    }}>
                      {info.name}: {info.count}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl">
      <PageHeader
        title="Trading Signals"
        subtitle="Anomalies, flow changes, and price movements across all monitored corridors"
      />

      {signals.length === 0 ? (
        <Card>
          <div className="text-center py-10">
            <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              No active signals detected. Markets are quiet across all monitored corridors.
            </div>
            <div className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
              {status?.total_records
                ? `${status.total_records.toLocaleString()} records analyzed across ${status.commodities_loaded} commodities`
                : 'Signals will appear when price movements, flow changes, or counterparty anomalies are detected'}
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
