import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { HarvestJob, RecordStat, HarvestResult } from '../api/client';
import { Card, PageHeader, MetricCard } from '../components/Cards';
import { Play, Database, RefreshCw } from 'lucide-react';

export default function DataManager() {
  const [jobs, setJobs] = useState<HarvestJob[]>([]);
  const [stats, setStats] = useState<RecordStat[]>([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [harvesting, setHarvesting] = useState(false);
  const [harvestResults, setHarvestResults] = useState<HarvestResult[]>([]);
  const [runningJob, setRunningJob] = useState<string | null>(null);

  const loadData = () => {
    api.listHarvestJobs().then((d) => setJobs(d.jobs)).catch(() => {});
    api.recordStats().then((d) => {
      setStats(d.record_stats);
      setTotalRecords(d.total_records);
    }).catch(() => {});
  };

  useEffect(() => { loadData(); }, []);

  const runJob = async (jobName: string) => {
    setRunningJob(jobName);
    setHarvesting(true);
    try {
      const result = await api.runHarvest({ job_name: jobName });
      setHarvestResults((prev) => [...result.harvest_results, ...prev]);
      loadData();
    } catch {
      // ignore
    } finally {
      setHarvesting(false);
      setRunningJob(null);
    }
  };

  const runAll = async (priority?: number) => {
    setHarvesting(true);
    setRunningJob('ALL');
    try {
      const result = await api.runHarvest({ priority });
      setHarvestResults((prev) => [...result.harvest_results, ...prev]);
      loadData();
    } catch {
      // ignore
    } finally {
      setHarvesting(false);
      setRunningJob(null);
    }
  };

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title="Data Management"
        subtitle="Harvest trade data from Eximpedia, monitor record counts, and manage data freshness"
      />

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Total Records" value={totalRecords.toLocaleString()} accent="cyan" />
        <MetricCard label="Commodities Tracked" value={stats.length} accent="blue" />
        <MetricCard label="Harvest Jobs" value={jobs.length} accent="amber" />
        <MetricCard
          label="Data Status"
          value={totalRecords > 0 ? 'Active' : 'Empty'}
          accent={totalRecords > 0 ? 'green' : 'red'}
        />
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => runAll(1)}
          disabled={harvesting}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-md transition-colors disabled:opacity-50"
          style={{ background: 'var(--accent-cyan)', color: '#000' }}
        >
          {harvesting && runningJob === 'ALL' ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          Harvest Priority 1 Jobs
        </button>
        <button
          onClick={() => runAll()}
          disabled={harvesting}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-md border transition-colors disabled:opacity-50"
          style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
        >
          <Database className="w-4 h-4" />
          Harvest All Jobs
        </button>
      </div>

      {/* Record stats */}
      {stats.length > 0 && (
        <Card className="mb-6">
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Record Inventory
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr style={{ color: 'var(--text-muted)' }}>
                  <th className="text-left py-2 px-2">Commodity</th>
                  <th className="text-right py-2 px-2">Records</th>
                  <th className="text-left py-2 px-2">Earliest</th>
                  <th className="text-left py-2 px-2">Latest</th>
                  <th className="text-left py-2 px-2">Origins</th>
                </tr>
              </thead>
              <tbody>
                {stats.map((s) => (
                  <tr key={s.hct_id} className="border-t" style={{ borderColor: 'var(--border)' }}>
                    <td className="py-2 px-2" style={{ color: 'var(--text-primary)' }}>{s.hct_name}</td>
                    <td className="text-right py-2 px-2 tabular-nums">{s.record_count.toLocaleString()}</td>
                    <td className="py-2 px-2" style={{ color: 'var(--text-secondary)' }}>{s.date_range.earliest ?? '---'}</td>
                    <td className="py-2 px-2" style={{ color: 'var(--text-secondary)' }}>{s.date_range.latest ?? '---'}</td>
                    <td className="py-2 px-2">
                      <div className="flex flex-wrap gap-1">
                        {s.origins.map((o) => (
                          <span key={o} className="text-[10px] px-1 py-0.5 rounded"
                            style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                            {o}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Harvest jobs */}
      <Card className="mb-6">
        <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
          Harvest Jobs
        </div>
        <div className="space-y-2">
          {jobs.map((j) => (
            <div key={j.name} className="flex items-center justify-between py-2 border-t"
              style={{ borderColor: 'var(--border)' }}>
              <div>
                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{j.name}</span>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] px-1.5 py-0.5 rounded"
                    style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                    {j.trade_type}
                  </span>
                  <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    {j.trade_country} | HS: {j.hs_codes?.join(', ')}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded"
                    style={{
                      background: j.priority === 1 ? 'rgba(6,182,212,0.1)' : 'var(--bg-secondary)',
                      color: j.priority === 1 ? 'var(--accent-cyan)' : 'var(--text-muted)',
                    }}>
                    P{j.priority}
                  </span>
                </div>
              </div>
              <button
                onClick={() => runJob(j.name)}
                disabled={harvesting}
                className="text-xs px-3 py-1 rounded border transition-colors disabled:opacity-50"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
              >
                {runningJob === j.name ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  'Run'
                )}
              </button>
            </div>
          ))}
        </div>
      </Card>

      {/* Recent harvest results */}
      {harvestResults.length > 0 && (
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
            Recent Harvest Results
          </div>
          <div className="space-y-2">
            {harvestResults.slice(0, 20).map((r, i) => (
              <div key={i} className="flex items-center justify-between py-1 text-xs">
                <span style={{ color: 'var(--text-primary)' }}>{r.job_name}</span>
                <div className="flex items-center gap-3">
                  <span className="tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                    {r.raw_count} raw → {r.normalized_count} normalized
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                    background: r.status === 'SUCCESS' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
                    color: r.status === 'SUCCESS' ? 'var(--accent-green)' : 'var(--accent-red)',
                  }}>
                    {r.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
