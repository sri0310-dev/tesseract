import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { HarvestJob, RecordStat, HarvestResult, HarvestSearchResult } from '../api/client';
import { Card, PageHeader, MetricCard } from '../components/Cards';
import { Play, Database, RefreshCw, Search } from 'lucide-react';

export default function DataManager() {
  const [jobs, setJobs] = useState<HarvestJob[]>([]);
  const [stats, setStats] = useState<RecordStat[]>([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [harvesting, setHarvesting] = useState(false);
  const [harvestResults, setHarvestResults] = useState<HarvestResult[]>([]);
  const [runningJob, setRunningJob] = useState<string | null>(null);

  // Search harvest
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<HarvestSearchResult | null>(null);

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

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setSearchResult(null);
    try {
      const result = await api.harvestBySearch(searchQuery.trim());
      setSearchResult(result);
      loadData(); // Refresh stats
    } catch {
      setSearchResult({ status: 'ERROR', commodity_query: searchQuery, commodities_matched: [], jobs_executed: 0, total_records_loaded: 0, results: [] });
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl">
      <PageHeader
        title="Data Management"
        subtitle="Search for any commodity to fetch data, or manage existing harvest jobs"
      />

      {/* Search by commodity name */}
      <Card className="mb-6">
        <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>
          Fetch Commodity Data
        </div>
        <div className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
          Type a commodity name (e.g. "cashew", "sesame", "rice", "cotton") — the system will
          auto-resolve HS codes and pull data from Eximpedia.
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="e.g. cashew, sesame, palm oil, cocoa..."
            className="flex-1 text-sm rounded-md px-3 py-2 border outline-none"
            style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            disabled={searching}
          />
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="flex items-center gap-2 text-sm px-4 py-2 rounded-md transition-colors disabled:opacity-50"
            style={{ background: 'var(--accent-cyan)', color: '#000' }}
          >
            {searching ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            {searching ? 'Fetching...' : 'Fetch Data'}
          </button>
        </div>

        {searchResult && (
          <div className="mt-3 p-3 rounded-md text-xs" style={{
            background: searchResult.status === 'SUCCESS' ? 'rgba(34,197,94,0.1)' :
              searchResult.status === 'NOT_FOUND' ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)',
          }}>
            {searchResult.status === 'SUCCESS' ? (
              <div>
                <span style={{ color: 'var(--accent-green)' }}>
                  Loaded {searchResult.total_records_loaded.toLocaleString()} records
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {' '}for {searchResult.commodities_matched.join(', ')}
                  {' '}({searchResult.jobs_executed} jobs executed)
                </span>
              </div>
            ) : searchResult.status === 'NOT_FOUND' ? (
              <div>
                <span style={{ color: 'var(--accent-amber)' }}>
                  No match for "{searchResult.commodity_query}".
                </span>
                {searchResult.available && (
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {' '}Try: {searchResult.available.join(', ')}
                  </span>
                )}
              </div>
            ) : (
              <span style={{ color: 'var(--accent-red)' }}>Search failed. Please try again.</span>
            )}
          </div>
        )}
      </Card>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Total Records" value={totalRecords.toLocaleString()} accent="cyan" />
        <MetricCard label="Commodities Tracked" value={stats.length} accent="blue" />
        <MetricCard label="Harvest Jobs" value={jobs.length} accent="amber" />
        <MetricCard
          label="Data Status"
          value={totalRecords > 0 ? 'Active' : 'Loading...'}
          accent={totalRecords > 0 ? 'green' : 'amber'}
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
          Refresh Priority Data
        </button>
        <button
          onClick={() => runAll()}
          disabled={harvesting}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-md border transition-colors disabled:opacity-50"
          style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
        >
          <Database className="w-4 h-4" />
          Refresh All Data
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
          Configured Harvest Jobs
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
                    {r.raw_count} raw &rarr; {r.normalized_count} normalized
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
