import type { ReactNode } from 'react';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-lg border p-4 ${className}`}
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
    >
      {children}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number | null;
  sub?: string;
  accent?: 'green' | 'red' | 'amber' | 'blue' | 'cyan';
}) {
  const colorMap = {
    green: 'var(--accent-green)',
    red: 'var(--accent-red)',
    amber: 'var(--accent-amber)',
    blue: 'var(--accent-blue)',
    cyan: 'var(--accent-cyan)',
  };
  const accentColor = accent ? colorMap[accent] : 'var(--text-primary)';

  return (
    <Card>
      <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div className="text-2xl font-semibold tabular-nums" style={{ color: accentColor }}>
        {value ?? '---'}
      </div>
      {sub && (
        <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
          {sub}
        </div>
      )}
    </Card>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, { bg: string; text: string }> = {
    HIGH: { bg: 'rgba(239,68,68,0.15)', text: 'var(--accent-red)' },
    MEDIUM: { bg: 'rgba(245,158,11,0.15)', text: 'var(--accent-amber)' },
    LOW: { bg: 'rgba(34,197,94,0.15)', text: 'var(--accent-green)' },
  };
  const s = styles[severity] ?? styles.LOW;
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider"
      style={{ background: s.bg, color: s.text }}
    >
      {severity}
    </span>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, { bg: string; text: string }> = {
    HIGH: { bg: 'rgba(34,197,94,0.15)', text: 'var(--accent-green)' },
    MEDIUM: { bg: 'rgba(245,158,11,0.15)', text: 'var(--accent-amber)' },
    LOW: { bg: 'rgba(239,68,68,0.15)', text: 'var(--accent-red)' },
    NONE: { bg: 'rgba(100,116,139,0.15)', text: 'var(--text-muted)' },
  };
  const s = styles[confidence] ?? styles.NONE;
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider"
      style={{ background: s.bg, color: s.text }}
    >
      {confidence}
    </span>
  );
}

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="text-4xl mb-3 opacity-30">~</div>
      <div style={{ color: 'var(--text-muted)' }}>{message}</div>
      <div className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
        Data loads automatically on startup. Visit the Data page to fetch additional commodities.
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h1>
      {subtitle && (
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{subtitle}</p>
      )}
    </div>
  );
}
