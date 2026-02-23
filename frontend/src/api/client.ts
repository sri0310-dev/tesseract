const BASE = (import.meta.env.VITE_API_URL || '') + '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) });
}

function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

// ── Intelligence endpoints ─────────────────────────────────────

export const api = {
  // Signals
  getSignals: (limit = 20) => get<{ signals: Signal[]; total: number }>(
    `/intelligence/signals?limit=${limit}`
  ),

  // Commodities
  listCommodities: () => get<{ commodities: CommodityListItem[] }>(
    '/intelligence/commodities'
  ),

  commodityDeepDive: (params: DeepDiveParams) =>
    post<DeepDiveResult>('/intelligence/commodity/deep-dive', params),

  // Corridors
  listCorridors: () => get<{ corridors: CorridorListItem[] }>(
    '/intelligence/corridors'
  ),

  analyzeCorridor: (params: CorridorAnalyzeParams) =>
    post<CorridorResult>('/intelligence/corridor/analyze', params),

  compareCorridors: (params: CorridorCompareParams) =>
    post<CorridorCompareResult>('/intelligence/corridor/compare', params),

  // Counterparty
  marketShares: (params: CounterpartyParams) =>
    post<MarketShareResult>('/intelligence/counterparty/market-shares', params),

  counterpartyAnomalies: (params: CounterpartyParams) =>
    post<{ anomalies: Anomaly[] }>('/intelligence/counterparty/anomalies', params),

  // S&D
  sdDelta: (params: SDDeltaParams) =>
    post<SDDeltaResult>('/intelligence/sd/delta', params),

  sdFlows: (params: DeepDiveParams) =>
    post<FlowResult>('/intelligence/sd/flows', params),

  // Arbitrage
  arbitrageScan: (hctId: string) =>
    get<{ commodity: string; opportunities: ArbOpportunity[] }>(
      `/intelligence/arbitrage/${hctId}`
    ),

  // Data management
  queryShipments: (params: ShipmentQueryParams) =>
    post<ShipmentQueryResult>('/data/query/shipments', params),

  runHarvest: (params: { job_name?: string; priority?: number }) =>
    post<{ harvest_results: HarvestResult[] }>('/data/harvest/run', params),

  listHarvestJobs: () => get<{ jobs: HarvestJob[] }>('/data/harvest/jobs'),

  recordStats: () => get<{ record_stats: RecordStat[]; total_records: number }>(
    '/data/records/stats'
  ),

  submitGroundPrice: (price: GroundPriceInput) =>
    post<{ status: string; observation: unknown }>('/data/ground-price', price),

  // Search harvest — type a commodity name and auto-fetch data
  harvestBySearch: (commodityName: string) =>
    post<HarvestSearchResult>(`/data/harvest/search?commodity_name=${encodeURIComponent(commodityName)}`, {}),

  // Data loading status — check if initial harvest is done
  harvestStatus: () => get<HarvestStatus>('/data/harvest/status'),
};

// ── Types ──────────────────────────────────────────────────────

export interface Signal {
  signal_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  headline: string;
  detail: Record<string, unknown>;
  timestamp?: string;
  hct_id?: string;
}

export interface CommodityListItem {
  hct_id: string;
  hct_name: string;
  hct_group: string;
  hct_supergroup: string;
  record_count: number;
  current_price_usd: number | null;
  price_confidence: string;
  quality_grades: string[];
}

export interface DeepDiveParams {
  hct_id: string;
  start_date: string;
  end_date: string;
  origin_countries?: string[];
  destination_countries?: string[];
}

export interface DeepDiveResult {
  commodity: { hct_id: string; hct_name: string; hct_group: string };
  current_ipc: IPCResult;
  ipc_series: IPCPoint[];
  fvi: FVIResult;
  volume_summary: FlowResult;
  top_buyers: MarketShareResult;
  top_sellers: MarketShareResult;
  seasonal_patterns: unknown;
}

export interface IPCResult {
  price_usd_per_mt: number | null;
  confidence: string;
  n_records: number;
  volume_mt: number;
  price_iqr: number | null;
  price_min: number | null;
  price_max: number | null;
  price_mean: number | null;
  window_start: string | null;
  window_end: string | null;
}

export interface IPCPoint extends IPCResult {
  date: string;
}

export interface FVIResult {
  fvi_raw: number | null;
  fvi_adjusted?: number | null;
  signal: string;
  signal_adjusted?: string;
  volume_recent_mt: number;
  volume_baseline_mt: number;
  seasonal_factor?: number;
}

export interface CorridorListItem {
  id: string;
  name: string;
  commodity: string;
  origins: string[];
  destinations: string[];
  record_count: number;
  current_fob: number | null;
  price_confidence: string;
}

export interface CorridorAnalyzeParams {
  hct_id: string;
  origin_country: string;
  origin_port: string;
  dest_port: string;
  target_date?: string;
}

export interface CorridorResult {
  origin: string;
  origin_port: string;
  dest_port: string;
  fob_usd_per_mt: number | null;
  freight_usd_per_mt: number | null;
  insurance_usd_per_mt: number | null;
  port_charges_usd_per_mt: number | null;
  implied_cif_usd_per_mt: number | null;
  ipc_confidence: string;
}

export interface CorridorCompareParams {
  hct_id: string;
  origins: { country: string; port: string }[];
  dest_port: string;
  target_date?: string;
}

export interface CorridorCompareResult {
  destination_port: string;
  comparisons: CorridorResult[];
  cheapest_origin: string | null;
  origin_spread_usd: number | null;
  n_origins_with_data: number;
}

export interface CounterpartyParams {
  hct_id: string;
  party_type?: 'consignee' | 'consignor';
  start_date?: string;
  end_date?: string;
  top_n?: number;
}

export interface MarketShareResult {
  party_type: string;
  total_volume_mt: number;
  unique_entities: number;
  hhi: number;
  concentration: string;
  top_entities: EntityShare[];
}

export interface EntityShare {
  entity: string;
  volume_mt: number;
  value_usd: number;
  shipments: number;
  market_share_pct: number;
  avg_price_per_mt: number | null;
}

export interface Anomaly {
  type: string;
  entity: string;
  severity: string;
  detail: string;
  volume_mt?: number;
  market_share_pct?: number;
}

export interface SDDeltaParams {
  hct_id: string;
  consensus_annual_mt: number;
  crop_year_start: string;
  target_date?: string;
}

export interface SDDeltaResult {
  actual_cumulative_mt: number;
  expected_cumulative_mt: number;
  delta_mt: number;
  delta_pct: number;
  consensus_annual_mt: number;
  crop_year_progress_pct: number;
  signal: string;
  implication: string;
  country_breakdown: { country: string; volume_mt: number; share_pct: number }[];
}

export interface FlowResult {
  total_volume_mt: number;
  total_value_usd: number;
  record_count: number;
  avg_price_per_mt: number | null;
  country_breakdown: { country: string; volume_mt: number; share_pct: number }[];
  daily_series: { date: string; daily_volume_mt: number; cumulative_volume_mt: number }[];
}

export interface ArbOpportunity {
  cheaper_origin: string;
  expensive_origin: string;
  cheaper_fob: number;
  expensive_fob: number;
  spread_usd: number;
  spread_pct: number;
  confidence: string;
}

export interface ShipmentQueryParams {
  start_date: string;
  end_date: string;
  trade_type: 'IMPORT' | 'EXPORT';
  trade_country: string;
  hs_codes?: number[];
  products?: string[];
  origin_countries?: string[];
  destination_countries?: string[];
  page_size?: number;
  page_no?: number;
}

export interface ShipmentQueryResult {
  total_records: number;
  page: number;
  raw_count: number;
  normalized_count: number;
  records: NormalizedRecord[];
}

export interface NormalizedRecord {
  record_id: string;
  trade_date: string;
  trade_type: string;
  consignee: string | null;
  consignor: string | null;
  origin_country: string | null;
  destination_country: string | null;
  hct_id: string | null;
  hct_name: string;
  quantity_mt: number | null;
  fob_usd_per_mt: number | null;
  fob_usd_total: number | null;
  price_status: string;
  quality_estimate: { grade: string; confidence: number };
}

export interface HarvestResult {
  job_name: string;
  status: string;
  raw_count: number;
  normalized_count: number;
  error_count?: number;
}

export interface HarvestJob {
  name: string;
  trade_type: string;
  trade_country: string;
  hs_codes: number[];
  priority: number;
}

export interface RecordStat {
  hct_id: string;
  hct_name: string;
  record_count: number;
  date_range: { earliest: string | null; latest: string | null };
  origins: string[];
}

export interface GroundPriceInput {
  hct_id: string;
  price: number;
  currency: string;
  unit: string;
  incoterm: string;
  location: string;
  quality_grade?: string;
  source_type: string;
  source_name?: string;
  observation_date: string;
  notes?: string;
}

export interface HarvestSearchResult {
  status: string;
  commodity_query: string;
  commodities_matched: string[];
  jobs_executed: number;
  total_records_loaded: number;
  results: HarvestResult[];
  message?: string;
  available?: string[];
}

export interface HarvestStatus {
  total_records: number;
  commodities_loaded: number;
  total_commodities: number;
  loading_complete: boolean;
  per_commodity: Record<string, { name: string; count: number }>;
}
