export type WindowId = '2017-02' | '2017-03'
export type ViewId = 'overview' | 'cohorts' | 'segments' | 'subscribers' | 'scenario' | 'data' | 'definitions'

export type Meta = {
  as_of: string
  release_id: string
  mode: 'private' | 'public'
  metric_version: string
  filters: Record<string, string>
}

export type Envelope<T> = { data: T; meta: Meta }

export const isStaticPublic = import.meta.env.VITE_RETENTION_STATIC_PUBLIC === '1'

export type SourceAttribution = {
  provider: string
  collection: string
  source_url: string
  usage: string
}

export type Overview = {
  label_window: WindowId
  history_cutoff: string
  eligible_subscribers: number
  active_subscribers: number
  observed_renewed_subscribers: number
  observed_churned_subscribers: number
  observed_renewal_rate: number
  observed_churn_rate: number
  gross_receipts_lifetime: number
  gross_receipts_30d: number
  gross_receipts_90d: number
  subscription_event_count_lifetime: number
  cancellation_event_count_lifetime: number
  cancellation_event_rate: number
  listening_active_days_30d: number
  listening_active_days_90d: number
  full_completion_count_30d: number
  negative_duration_rows_90d: number
}

export type Cohort = {
  label_window: WindowId
  registration_cohort_month: string
  eligible_subscribers: number
  observed_renewed_subscribers: number
  observed_churned_subscribers: number
  observed_renewal_rate: number
  observed_churn_rate: number
  gross_receipts_90d: number
}

export type Segment = {
  label_window: WindowId
  dimension?: string
  segment_key?: string
  segment_label?: string
  engagement_segment?: string
  eligible_subscribers: number
  observed_renewed_subscribers: number
  observed_churned_subscribers: number
  observed_renewal_rate?: number
  observed_churn_rate: number
  gross_receipts_90d?: number
  average_listening_active_days_30d?: number
  average_listening_seconds_30d?: number
  full_completion_count_30d?: number
}

export type Definition = {
  metric_id: string
  definition: string
  grain: string
  direction: string
  limitation: string
}

export type Subscriber = {
  subscriber_token: string
  label_window: WindowId
  is_churn: number
  is_active_at_cutoff: boolean
  effective_expiration_date: string
  engagement_segment: string
  gross_receipts_90d: number
  listening_active_days_30d: number
  latest_payment_plan_days: number
  latest_is_auto_renew: number
}

export type Journey = {
  profile: Record<string, string | number | boolean | null>
  transactions: Array<Record<string, string | number | boolean | null>>
  listening_monthly: Array<Record<string, string | number | boolean | null>>
}

export type ScenarioInputs = {
  capacity: number
  minimum_score: number
  contact_cost: number
  offer_cost: number
  assumed_lift: number
  lift_uncertainty: number
}

export type ScenarioOutcome = {
  assumed_lift: number
  simulated_retained_subscribers: number
  simulated_retained_gross_receipt_proxy: number
  contact_spend: number
  offer_spend: number
  total_spend: number
  simulated_net_value: number
  simulated_roi: number | null
  break_even_lift: number | null
  break_even_feasible: boolean
}

export type Scenario = {
  status: 'simulated'
  scope: 'repeat_subscribers_only'
  score_window: '2017-03'
  requested: ScenarioInputs
  selection: {
    contacts: number
    minimum_score: number
    expected_churners: number
    observed_churners: number
    risk_weighted_payment_proxy: number
    selected_payment_proxy: number
    observed_churn_rate: number
    modeled_risk_capture: number
    capacity_utilization: number | null
    eligible_subscribers: number
    new_subscribers_excluded: boolean
  }
  outcomes: Record<'low' | 'expected' | 'high', ScenarioOutcome>
  definitions: Record<'assumed_lift' | 'offer_cost' | 'value_proxy' | 'limitation', string>
}

type StaticSnapshot = {
  status: Envelope<{ freshness: string; attribution: SourceAttribution }>
  overview: Record<WindowId, Envelope<Overview>>
  cohorts: Record<WindowId, Envelope<Cohort[]>>
  segments: Record<WindowId, Record<string, Envelope<Segment[]>>>
  definitions: Envelope<Definition[]>
}

let snapshotRequest: Promise<StaticSnapshot> | null = null

function loadStaticSnapshot(): Promise<StaticSnapshot> {
  snapshotRequest ??= fetch('/data/public-snapshot.json').then(async (response) => {
    if (!response.ok) throw new Error(`Public snapshot failed with status ${response.status}`)
    return response.json()
  })
  return snapshotRequest
}

async function getStatic<T>(path: string, signal?: AbortSignal): Promise<Envelope<T>> {
  const snapshot = await loadStaticSnapshot()
  if (signal?.aborted) throw new DOMException('Request aborted', 'AbortError')
  const url = new URL(path, window.location.origin)
  const windowId = (url.searchParams.get('label_window') || '2017-03') as WindowId

  if (url.pathname === '/api/v1/status') return snapshot.status as Envelope<T>
  if (url.pathname === '/api/v1/definitions') return snapshot.definitions as Envelope<T>
  if (url.pathname === '/api/v1/overview') return snapshot.overview[windowId] as Envelope<T>
  if (url.pathname === '/api/v1/cohorts') return snapshot.cohorts[windowId] as Envelope<T>
  if (url.pathname === '/api/v1/segments') {
    const dimension = url.searchParams.get('dimension') || 'engagement'
    return snapshot.segments[windowId][dimension] as Envelope<T>
  }
  throw new Error('This route is unavailable in the aggregate public release')
}

export function exportHref(windowId: WindowId): string {
  return isStaticPublic
    ? `/exports/retention-overview-${windowId}.csv`
    : `/api/v1/export/overview.csv?label_window=${windowId}`
}

export async function get<T>(path: string, signal?: AbortSignal): Promise<Envelope<T>> {
  if (isStaticPublic) return getStatic<T>(path, signal)
  const response = await fetch(path, { signal })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: 'Unknown response' }))
    throw new Error(payload.detail || `Request failed with status ${response.status}`)
  }
  return response.json()
}

export async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<Envelope<T>> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: 'Unknown response' }))
    throw new Error(payload.detail || `Request failed with status ${response.status}`)
  }
  return response.json()
}
