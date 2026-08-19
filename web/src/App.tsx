/*
THESIS: Retention review begins with comparable evidence rows, refusing the dashboard hero and KPI-card sequence.
OWN-WORLD: Near-black navy headers, white working fields, cool rules, tabular numerals, amber adverse marks, and green validation marks.
STORY: Find a material movement, inspect its arithmetic and limits, then compare matching cohort and segment breaks.
FIRST VIEWPORT: A compact product bar and comparison rail sit above a wide movement blotter with a synchronized evidence inspector.
FORM: Exception-first operating blotter, structure five, staged as one active analytical desk with supporting tables held below.
*/
import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import type { EChartsCoreOption as ChartOption } from 'echarts/core'
import {
  type Cohort,
  type Definition,
  type Overview,
  type Segment,
  type Scenario,
  type ScenarioInputs,
  type SourceAttribution,
  type ViewId,
  type WindowId,
  exportHref,
  get,
} from './api'
import DataCatalogView from './DataCatalogView'

const isStaticPublicBuild = import.meta.env.VITE_RETENTION_STATIC_PUBLIC === '1'
const Chart = lazy(() => import('./Chart'))
const SubscriberView = isStaticPublicBuild ? null : lazy(() => import('./SubscriberView'))
const ScenarioView = isStaticPublicBuild ? null : lazy(() => import('./ScenarioView'))
const initialScenarioInputs: ScenarioInputs = { capacity: 50000, minimum_score: 0.1, contact_cost: 0.5, offer_cost: 2, assumed_lift: 0.12, lift_uncertainty: 0.04 }

const views: Array<{ id: ViewId; label: string; brief: string }> = [
  { id: 'overview', label: 'Overview', brief: 'Movement and observed outcome' },
  { id: 'cohorts', label: 'Cohorts', brief: 'Registration-month persistence' },
  { id: 'segments', label: 'Segments', brief: 'Plan, payment, channel, listening' },
  ...(isStaticPublicBuild
    ? []
    : [
        { id: 'subscribers' as const, label: 'Journeys', brief: 'Pseudonymous record review' },
        { id: 'scenario' as const, label: 'Scenario', brief: 'Capacity, lift, cost sensitivity' },
      ]),
  { id: 'data', label: 'Data', brief: 'Row-level Parquet release' },
  { id: 'definitions', label: 'Definitions', brief: 'Grain, direction, limitation' },
]

const dimensions = [
  ['engagement', 'Engagement'],
  ['payment_method', 'Payment'],
  ['plan_days', 'Plan'],
  ['registration_method', 'Registration'],
  ['auto_renew', 'Auto-renew'],
] as const

const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 })
const integer = new Intl.NumberFormat('en-US')
const percent = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 })

function DeferredChart({ option, label }: { option: ChartOption; label: string }) {
  return <Suspense fallback={<div className="chart chart-loading" role="status">Preparing governed chart</div>}><Chart option={option} label={label} /></Suspense>
}

type MovementId = 'active_subscribers' | 'observed_renewal_rate' | 'observed_churn_rate' | 'gross_receipts_30d' | 'cancellation_event_rate' | 'listening_active_days_30d'
type Movement = {
  id: MovementId
  label: string
  current: number
  comparison: number
  format: (value: number) => string
  deltaKind: 'count' | 'rate' | 'amount'
  direction: 'higher' | 'lower' | 'context'
  basis: string
  definitionId: string
}

const signed = (value: number, format: (amount: number) => string) => `${value > 0 ? '+' : value < 0 ? '-' : ''}${format(Math.abs(value))}`
const segmentKey = (row: Segment) => row.segment_key || row.engagement_segment || row.segment_label || 'Unknown'
const segmentLabel = (row: Segment) => row.segment_label || row.engagement_segment || row.segment_key || 'Unknown'

function App() {
  const [windowId, setWindowId] = useState<WindowId>('2017-03')
  const [view, setView] = useState<ViewId>('overview')
  const [dimension, setDimension] = useState<(typeof dimensions)[number][0]>('engagement')
  const [scenarioInputs, setScenarioInputs] = useState(initialScenarioInputs)
  const [scenario, setScenario] = useState<Scenario | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [prior, setPrior] = useState<Overview | null>(null)
  const [cohorts, setCohorts] = useState<Cohort[]>([])
  const [comparisonCohorts, setComparisonCohorts] = useState<Cohort[]>([])
  const [segments, setSegments] = useState<Segment[]>([])
  const [comparisonSegments, setComparisonSegments] = useState<Segment[]>([])
  const [definitions, setDefinitions] = useState<Definition[]>([])
  const [mode, setMode] = useState<'private' | 'public'>('private')
  const [attribution, setAttribution] = useState<SourceAttribution | null>(null)
  const [freshness, setFreshness] = useState('Checking semantic warehouse')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [segmentsLoading, setSegmentsLoading] = useState(true)
  const [scan, setScan] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    Promise.all([
      get<Overview>(`/api/v1/overview?label_window=${windowId}`, controller.signal),
      get<Overview>(`/api/v1/overview?label_window=${windowId === '2017-03' ? '2017-02' : '2017-03'}`, controller.signal),
      get<Cohort[]>(`/api/v1/cohorts?label_window=${windowId}&limit=240`, controller.signal),
      get<Cohort[]>(`/api/v1/cohorts?label_window=${windowId === '2017-03' ? '2017-02' : '2017-03'}&limit=240`, controller.signal),
      get<Definition[]>('/api/v1/definitions', controller.signal),
      get<{ freshness: string; attribution: SourceAttribution }>('/api/v1/status', controller.signal),
    ])
      .then(([current, comparison, cohortData, comparisonCohortData, definitionData, status]) => {
        setOverview(current.data)
        setPrior(comparison.data)
        setCohorts(cohortData.data)
        setComparisonCohorts(comparisonCohortData.data)
        setDefinitions(definitionData.data)
        setFreshness(status.data.freshness)
        setAttribution(status.data.attribution)
        setMode(status.meta.mode)
        setScan((value) => value + 1)
      })
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [windowId])

  useEffect(() => {
    const controller = new AbortController()
    setSegmentsLoading(true)
    Promise.all([
      get<Segment[]>(`/api/v1/segments?label_window=${windowId}&dimension=${dimension}&limit=50`, controller.signal),
      get<Segment[]>(`/api/v1/segments?label_window=${windowId === '2017-03' ? '2017-02' : '2017-03'}&dimension=${dimension}&limit=50`, controller.signal),
    ])
      .then(([current, comparison]) => {
        setSegments(current.data)
        setComparisonSegments(comparison.data)
      })
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setSegmentsLoading(false)
      })
    return () => controller.abort()
  }, [windowId, dimension])

  const segmentOption = useMemo<ChartOption>(() => ({
    animationDuration: 380,
    grid: { left: 8, right: 18, top: 10, bottom: 22, containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: (value: number) => `${value}%` }, splitLine: { lineStyle: { color: '#d9deda' } } },
    yAxis: { type: 'category', data: segments.slice(0, 10).map((item) => item.segment_label || item.engagement_segment || 'Unknown'), axisLine: { show: false }, axisTick: { show: false } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (value: unknown) => `${Number(value).toFixed(1)}% observed churn` },
    series: [{ type: 'bar', data: segments.slice(0, 10).map((item) => item.observed_churn_rate * 100), barWidth: 13, itemStyle: { color: '#a4482f', borderRadius: [0, 2, 2, 0] } }],
  }), [segments])

  const activeView = mode === 'public' && ['subscribers', 'scenario'].includes(view) ? 'overview' : view

  return (
    <div className="app-shell">
      <header className="masthead">
        <p className="product-name">Subscriber Retention Intelligence</p>
        <nav className="module-nav" aria-label="Retention analysis views">
          {views.filter((item) => mode === 'private' || !['subscribers', 'scenario'].includes(item.id)).map((item) => (
            <button key={item.id} className={activeView === item.id ? 'active' : ''} onClick={() => { setView(item.id); if (item.id === 'scenario') setWindowId('2017-03') }} aria-current={activeView === item.id ? 'page' : undefined} title={item.brief}>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="status-line" aria-label="Product status">
          <span className="status-dot" aria-hidden="true" />
          <span className="mode-stamp">{mode}</span>
          <span className="freshness">{freshness}</span>
        </div>
      </header>

      <div className="priority-strip" aria-label="Analysis controls">
        <div className="window-control">
          <span>{activeView === 'scenario' ? 'Score window' : activeView === 'data' ? 'Release' : 'Label window'}</span>
          {activeView === 'data'
            ? <strong>public-m12</strong>
            : activeView === 'scenario'
            ? <strong>March 2017</strong>
            : <div className="segmented" role="group" aria-label="Observed label window">
              {(['2017-02', '2017-03'] as WindowId[]).map((item) => (
                <button key={item} className={windowId === item ? 'active' : ''} onClick={() => setWindowId(item)} aria-pressed={windowId === item}>{item}</button>
              ))}
            </div>}
        </div>
        <div><span>{activeView === 'data' ? 'Publication grain' : 'History cutoff'}</span><strong>{activeView === 'data' ? 'Row-level Parquet' : activeView === 'scenario' ? '2017-02-28' : overview?.history_cutoff || 'Loading'}</strong></div>
        <div><span>{activeView === 'data' ? 'Published rows' : activeView === 'scenario' ? 'Eligible repeat subscribers' : 'Eligible population'}</span><strong>{activeView === 'data' ? integer.format(442211685) : activeView === 'scenario' ? integer.format(scenario?.selection.eligible_subscribers ?? 881701) : overview ? integer.format(overview.eligible_subscribers) : 'Loading'}</strong></div>
        {activeView === 'data'
          ? <span className="export-link data-format">Zstd · 7.52 GB</span>
          : <a className="export-link" href={exportHref(windowId)} download>Export governed CSV</a>}
      </div>

      <div className="workspace">
        <main id="main-content" className={`evidence-ledger scan-${scan}`} tabIndex={-1}>
          {loading && <div className="state-panel" role="status"><span className="loading-mark" />Recomputing evidence for {windowId}</div>}
          {error && <div className="state-panel error" role="alert"><strong>Evidence unavailable</strong><p>{error}</p><button onClick={() => location.reload()}>Retry product</button></div>}
          {!loading && !error && overview && prior && (
            <>
              {activeView === 'overview' && <OverviewView current={overview} comparison={prior} cohorts={cohorts} comparisonCohorts={comparisonCohorts} segments={segments} comparisonSegments={comparisonSegments} definitions={definitions} dimension={dimension} setDimension={setDimension} segmentsLoading={segmentsLoading} />}
              {activeView === 'cohorts' && <CohortView cohorts={cohorts} />}
              {activeView === 'segments' && <SegmentView segments={segments} dimension={dimension} setDimension={setDimension} option={segmentOption} loading={segmentsLoading} />}
              {activeView === 'subscribers' && mode === 'private' && SubscriberView && <Suspense fallback={<div className="state-panel" role="status"><span className="loading-mark" />Preparing private journey review</div>}><SubscriberView windowId={windowId} /></Suspense>}
              {activeView === 'scenario' && mode === 'private' && ScenarioView && <Suspense fallback={<div className="state-panel" role="status"><span className="loading-mark" />Preparing scenario docket</div>}><ScenarioView inputs={scenarioInputs} setInputs={setScenarioInputs} scenario={scenario} setScenario={setScenario} /></Suspense>}
              {activeView === 'data' && <DataCatalogView />}
              {activeView === 'definitions' && <DefinitionsView definitions={definitions} />}
            </>
          )}
        </main>

        {!['scenario', 'overview', 'data'].includes(activeView) && <aside className="definition-rail" aria-label="Metric guardrails">
          <p className="rail-title">Interpretation guardrails</p>
          <div className="guardrail-list">
            <DefinitionBrief title="Observed churn" body="Challenge-compatible failure to renew inside the defined 30-day gap. Lower is favorable." />
            <DefinitionBrief title="Gross receipts" body="Actual amount paid in source currency. Not recognized revenue, MRR, or ARR." />
            <DefinitionBrief title="Active at cutoff" body="Reconstructed effective expiration is on or after the history cutoff." />
            <DefinitionBrief title="Listening" body="Recorded subscriber-days before cutoff. Missing activity is not proof of inactivity." />
          </div>
          <button className="text-button" onClick={() => setView('definitions')}>Open all definitions</button>
        </aside>}
      </div>
      {attribution && <footer className="source-footer" aria-label="Source attribution">
        <div><strong>Source boundary</strong><span>{attribution.usage}</span></div>
        <p><span>Data source: </span><a href={attribution.source_url}>{attribution.provider} · {attribution.collection}</a></p>
      </footer>}
    </div>
  )
}

function OverviewView({ current, comparison, cohorts, comparisonCohorts, segments, comparisonSegments, definitions, dimension, setDimension, segmentsLoading }: { current: Overview; comparison: Overview; cohorts: Cohort[]; comparisonCohorts: Cohort[]; segments: Segment[]; comparisonSegments: Segment[]; definitions: Definition[]; dimension: string; setDimension: (value: (typeof dimensions)[number][0]) => void; segmentsLoading: boolean }) {
  const movements: Movement[] = [
    { id: 'observed_churn_rate', label: 'Observed churn', current: current.observed_churn_rate, comparison: comparison.observed_churn_rate, format: percent.format, deltaKind: 'rate', direction: 'lower', basis: 'Observed label', definitionId: 'observed_churn_rate' },
    { id: 'active_subscribers', label: 'Active subscribers', current: current.active_subscribers, comparison: comparison.active_subscribers, format: integer.format, deltaKind: 'count', direction: 'higher', basis: 'Reconstructed', definitionId: 'active_subscribers' },
    { id: 'observed_renewal_rate', label: 'Observed renewal', current: current.observed_renewal_rate, comparison: comparison.observed_renewal_rate, format: percent.format, deltaKind: 'rate', direction: 'higher', basis: 'Observed label', definitionId: 'observed_renewal_rate' },
    { id: 'gross_receipts_30d', label: '30-day gross receipts', current: current.gross_receipts_30d, comparison: comparison.gross_receipts_30d, format: compact.format, deltaKind: 'amount', direction: 'context', basis: 'Source payment', definitionId: 'gross_receipts' },
    { id: 'cancellation_event_rate', label: 'Cancellation event rate', current: current.cancellation_event_rate, comparison: comparison.cancellation_event_rate, format: percent.format, deltaKind: 'rate', direction: 'lower', basis: 'Source events', definitionId: 'cancellation_event_rate' },
    { id: 'listening_active_days_30d', label: 'Listening active days · 30d', current: current.listening_active_days_30d, comparison: comparison.listening_active_days_30d, format: compact.format, deltaKind: 'count', direction: 'context', basis: 'Source activity', definitionId: 'listening_active_days' },
  ]
  const [selectedId, setSelectedId] = useState<MovementId>('observed_churn_rate')
  const selected = movements.find((movement) => movement.id === selectedId) || movements[0]
  const comparisonByCohort = new Map(comparisonCohorts.map((row) => [row.registration_cohort_month, row]))
  const cohortBreaks = cohorts
    .map((row) => ({ current: row, comparison: comparisonByCohort.get(row.registration_cohort_month) }))
    .filter((pair): pair is { current: Cohort; comparison: Cohort } => Boolean(pair.comparison))
    .slice(0, 7)
  const comparisonBySegment = new Map(comparisonSegments.map((row) => [segmentKey(row), row]))
  const segmentBreaks = segments
    .map((row) => ({ current: row, comparison: comparisonBySegment.get(segmentKey(row)) }))
    .filter((pair): pair is { current: Segment; comparison: Segment } => Boolean(pair.comparison))
    .sort((a, b) => b.current.observed_churn_rate - a.current.observed_churn_rate)
    .slice(0, 7)

  return <div className="analysis-blotter">
    <section className="movement-sheet" aria-labelledby="movement-title">
        <div className="sheet-heading"><div><span>Operating review</span><h1 id="movement-title">Material movements</h1></div><p>Select a row to inspect its arithmetic, definition, and limits.</p></div>
        <div className="blotter-table-wrap">
          <table className="movement-table">
            <thead><tr><th>Metric</th><th>{comparison.label_window}</th><th>{current.label_window}</th><th>Absolute change</th><th>Relative change</th><th>Evidence</th></tr></thead>
            <tbody>{movements.map((movement) => {
              const delta = movement.current - movement.comparison
              const relative = movement.comparison ? delta / Math.abs(movement.comparison) : 0
              const displayDelta = movement.deltaKind === 'rate' ? Number((delta * 100).toFixed(1)) : delta
              const displayRelative = Number((relative * 100).toFixed(1))
              const favorable = movement.direction === 'higher' ? displayDelta > 0 : movement.direction === 'lower' ? displayDelta < 0 : false
              const adverse = movement.direction === 'higher' ? displayDelta < 0 : movement.direction === 'lower' ? displayDelta > 0 : false
              const tone = adverse ? 'adverse' : favorable ? 'favorable' : 'context'
              const deltaText = movement.deltaKind === 'rate' ? `${displayDelta > 0 ? '+' : ''}${displayDelta.toFixed(1)} pp` : signed(delta, movement.deltaKind === 'amount' ? compact.format : integer.format)
              return <tr key={movement.id} className={selected.id === movement.id ? 'selected' : ''} data-tone={tone}>
                <td><button className="movement-select" onClick={() => setSelectedId(movement.id)} aria-pressed={selected.id === movement.id}><span aria-hidden="true">{selected.id === movement.id ? '▸' : ''}</span>{movement.label}</button></td>
                <td>{movement.format(movement.comparison)}</td><td>{movement.format(movement.current)}</td><td className="movement-delta">{deltaText}</td><td>{`${displayRelative > 0 ? '+' : ''}${displayRelative.toFixed(1)}%`}</td><td><span className={`basis-mark ${tone}`}>{movement.basis}</span></td>
              </tr>
            })}</tbody>
          </table>
        </div>
    </section>
    <MovementInspector movement={selected} current={current} comparison={comparison} definitions={definitions} segmentBreaks={segmentBreaks} />
    <CohortBreaks currentWindow={current.label_window} comparisonWindow={comparison.label_window} rows={cohortBreaks} />
    <section className="segment-breaks" aria-labelledby="segment-break-title">
      <div className="sheet-heading compact"><div><span>Comparable descriptive cuts</span><h2 id="segment-break-title">Segment breaks</h2></div><p>Ranked by current observed churn. Differences are associations, not causes or additive contributions.</p></div>
      <div className="dimension-tabs blotter-tabs" role="tablist" aria-label="Segment dimension">{dimensions.map(([id, label]) => <button key={id} role="tab" aria-selected={dimension === id} className={dimension === id ? 'active' : ''} onClick={() => setDimension(id)}>{label}</button>)}</div>
      {segmentBreaks.some(({ current: row, comparison: compared }) => Math.min(row.eligible_subscribers, compared.eligible_subscribers) < 100) && <p className="sample-warning">Small group: rows below 100 eligible subscribers are directional only and are excluded from the public release.</p>}
      {segmentsLoading ? <div className="table-loading" role="status"><span className="loading-mark" />Loading comparable segment rows</div> : segmentBreaks.length ? <div className="blotter-table-wrap" tabIndex={0} aria-label="Scrollable segment comparison table"><table><thead><tr><th>Segment</th><th>Population</th><th>{comparison.label_window}</th><th>{current.label_window}</th><th>Change</th><th>Basis</th></tr></thead><tbody>{segmentBreaks.map(({ current: row, comparison: compared }) => { const delta = Number(((row.observed_churn_rate - compared.observed_churn_rate) * 100).toFixed(1)); return <tr key={segmentKey(row)} className={Math.min(row.eligible_subscribers, compared.eligible_subscribers) < 100 ? 'small-sample' : ''}><td>{segmentLabel(row)}</td><td>{integer.format(row.eligible_subscribers)}</td><td>{percent.format(compared.observed_churn_rate)}</td><td>{percent.format(row.observed_churn_rate)}</td><td className={delta > 0 ? 'adverse-text' : delta < 0 ? 'favorable-text' : ''}>{`${delta > 0 ? '+' : ''}${delta.toFixed(1)} pp`}</td><td>{Math.min(row.eligible_subscribers, compared.eligible_subscribers) < 100 ? 'Small group' : 'Observed label'}</td></tr> })}</tbody></table></div> : <EmptyState title="No comparable segments" body="No matching segment rows meet the governed minimum group size in both windows." />}
    </section>
  </div>
}

function MovementInspector({ movement, current, comparison, definitions, segmentBreaks }: { movement: Movement; current: Overview; comparison: Overview; definitions: Definition[]; segmentBreaks: Array<{ current: Segment; comparison: Segment }> }) {
  const delta = movement.current - movement.comparison
  const displayDelta = movement.deltaKind === 'rate' ? Number((delta * 100).toFixed(1)) : delta
  const exactRateDelta = Number((delta * 100).toFixed(2))
  const relative = movement.comparison ? delta / Math.abs(movement.comparison) : 0
  const definition = definitions.find((item) => item.metric_id === movement.definitionId)
  const offset = Math.max(-26, Math.min(26, relative * 64))
  const reconciliation = movement.id === 'observed_churn_rate'
    ? [{ label: 'Churned subscribers', comparison: comparison.observed_churned_subscribers, current: current.observed_churned_subscribers }, { label: 'Eligible subscribers', comparison: comparison.eligible_subscribers, current: current.eligible_subscribers }]
    : movement.id === 'observed_renewal_rate'
      ? [{ label: 'Renewed subscribers', comparison: comparison.observed_renewed_subscribers, current: current.observed_renewed_subscribers }, { label: 'Eligible subscribers', comparison: comparison.eligible_subscribers, current: current.eligible_subscribers }]
      : movement.id === 'active_subscribers'
        ? [{ label: 'Reconstructed active', comparison: comparison.active_subscribers, current: current.active_subscribers }, { label: 'Eligible subscribers', comparison: comparison.eligible_subscribers, current: current.eligible_subscribers }]
        : movement.id === 'cancellation_event_rate'
          ? [{ label: 'Cancellation events', comparison: comparison.cancellation_event_count_lifetime, current: current.cancellation_event_count_lifetime }, { label: 'Subscription events', comparison: comparison.subscription_event_count_lifetime, current: current.subscription_event_count_lifetime }]
          : [{ label: movement.label, comparison: movement.comparison, current: movement.current }]

  return <aside className="movement-inspector" aria-live="polite" aria-labelledby="inspector-title">
    <div className="inspector-heading"><span>Selected movement</span><h2 id="inspector-title">{movement.label}</h2><strong>{movement.deltaKind === 'rate' ? `${displayDelta > 0 ? '+' : ''}${displayDelta.toFixed(1)} pp` : signed(delta, movement.deltaKind === 'amount' ? compact.format : integer.format)}</strong></div>
    <svg className="comparison-slope" viewBox="0 0 360 126" role="img" aria-label={`${movement.label}: ${movement.format(movement.comparison)} in ${comparison.label_window} and ${movement.format(movement.current)} in ${current.label_window}`}>
      <line x1="48" y1="58" x2="312" y2={58 - offset} />
      <circle cx="48" cy="58" r="5" /><circle cx="312" cy={58 - offset} r="5" />
      <text x="48" y="42" textAnchor="middle">{movement.format(movement.comparison)}</text><text x="312" y={42 - offset} textAnchor="middle">{movement.format(movement.current)}</text>
      <text x="48" y="108" textAnchor="middle">{comparison.label_window}</text><text x="312" y="108" textAnchor="middle">{current.label_window}</text>
    </svg>
    <section className="reconciliation"><h3>Arithmetic basis</h3><table><thead><tr><th>Component</th><th>{comparison.label_window}</th><th>{current.label_window}</th></tr></thead><tbody>{reconciliation.map((row) => <tr key={row.label}><td>{row.label}</td><td>{movement.deltaKind === 'amount' && reconciliation.length === 1 ? compact.format(row.comparison) : integer.format(row.comparison)}</td><td>{movement.deltaKind === 'amount' && reconciliation.length === 1 ? compact.format(row.current) : integer.format(row.current)}</td></tr>)}<tr><td>Reported value</td><td>{movement.format(movement.comparison)}</td><td>{movement.format(movement.current)}</td></tr></tbody></table>{movement.deltaKind === 'rate' && <p className="reconciliation-equation">Rate change: {(movement.current * 100).toFixed(2)}% − {(movement.comparison * 100).toFixed(2)}% = {exactRateDelta > 0 ? '+' : ''}{exactRateDelta.toFixed(2)} pp</p>}</section>
    <dl className="inspector-contract"><div><dt>Current cutoff</dt><dd>{current.history_cutoff}</dd></div><div><dt>Comparison cutoff</dt><dd>{comparison.history_cutoff}</dd></div><div><dt>Evidence</dt><dd>{movement.basis}</dd></div><div><dt>Direction</dt><dd>{definition?.direction || movement.direction}</dd></div></dl>
    <section className="inspector-copy"><h3>Definition</h3><p>{definition?.definition || 'Governed measure from the retention overview.'}</p><h3>Limitation</h3><p>{definition?.limitation || 'Interpret only inside the declared historical window.'}</p></section>
    <section className="inspector-segments"><h3>Highest current churn · selected dimension</h3>{segmentBreaks.slice(0, 5).map(({ current: row, comparison: compared }) => { const small = Math.min(row.eligible_subscribers, compared.eligible_subscribers) < 100; return <div key={segmentKey(row)} className={small ? 'small-sample' : ''}><span>{segmentLabel(row)}<small>{integer.format(row.eligible_subscribers)} eligible{small ? ' · small group' : ''}</small></span><strong>{percent.format(row.observed_churn_rate)}</strong><i aria-hidden="true" style={{ width: `${Math.min(100, row.observed_churn_rate * 400)}%` }} /></div> })}</section>
  </aside>
}

function CohortBreaks({ currentWindow, comparisonWindow, rows }: { currentWindow: WindowId; comparisonWindow: WindowId; rows: Array<{ current: Cohort; comparison: Cohort }> }) {
  return <section className="cohort-breaks" aria-labelledby="cohort-break-title"><div className="sheet-heading compact"><div><span>Matching registration months</span><h2 id="cohort-break-title">Cohort breaks</h2></div><p>Only cohorts present in both label windows are compared.</p></div>{rows.length ? <div className="blotter-table-wrap" tabIndex={0} aria-label="Scrollable cohort comparison table"><table><thead><tr><th>Registration cohort</th><th>Population</th><th>{comparisonWindow}</th><th>{currentWindow}</th><th>Change</th><th>90d receipts</th></tr></thead><tbody>{rows.map(({ current, comparison }) => <tr key={current.registration_cohort_month}><td>{current.registration_cohort_month.slice(0, 7)}</td><td>{integer.format(current.eligible_subscribers)}</td><td>{percent.format(comparison.observed_churn_rate)}</td><td>{percent.format(current.observed_churn_rate)}</td><td className={current.observed_churn_rate > comparison.observed_churn_rate ? 'adverse-text' : 'favorable-text'}>{`${current.observed_churn_rate > comparison.observed_churn_rate ? '+' : ''}${((current.observed_churn_rate - comparison.observed_churn_rate) * 100).toFixed(1)} pp`}</td><td>{compact.format(current.gross_receipts_90d)}</td></tr>)}</tbody></table></div> : <EmptyState title="No comparable cohorts" body="No registration cohort meets the public group threshold in both windows." />}</section>
}

function CohortView({ cohorts }: { cohorts: Cohort[] }) {
  if (!cohorts.length) return <EmptyState title="No eligible cohorts" body="This window has no privacy-safe registration cohorts." />
  return <div className="view-stack"><section className="ledger-opening"><div><p className="section-kicker">Registration-month analysis</p><h1>Registration cohort detail</h1></div><p className="opening-brief">Each row uses subscribers eligible for the selected label window. Cohort month is registration month, not contract start.</p></section><section className="evidence-section"><div className="table-wrap"><table><thead><tr><th>Registration cohort</th><th>Eligible</th><th>Observed renewal</th><th>Observed churn</th><th>Gross receipts · 90d</th></tr></thead><tbody>{cohorts.map((row) => <tr key={row.registration_cohort_month}><td>{row.registration_cohort_month.slice(0, 7)}</td><td>{integer.format(row.eligible_subscribers)}</td><td><span className="rate-cell"><span style={{ width: `${row.observed_renewal_rate * 100}%` }} />{percent.format(row.observed_renewal_rate)}</span></td><td>{percent.format(row.observed_churn_rate)}</td><td>{compact.format(row.gross_receipts_90d)}</td></tr>)}</tbody></table></div></section></div>
}

function SegmentView({ segments, dimension, setDimension, option, loading }: { segments: Segment[]; dimension: string; setDimension: (value: (typeof dimensions)[number][0]) => void; option: ChartOption; loading: boolean }) {
  return <div className="view-stack"><section className="ledger-opening"><div><p className="section-kicker">Descriptive comparison</p><h1>Observed churn by segment</h1></div><p className="opening-brief">Differences are descriptive. They do not prove channel, plan, payment, or listening behavior caused churn.</p></section><div className="dimension-tabs" role="tablist" aria-label="Segment dimension">{dimensions.map(([id, label]) => <button key={id} role="tab" aria-selected={dimension === id} className={dimension === id ? 'active' : ''} onClick={() => setDimension(id)}>{label}</button>)}</div>{loading ? <div className="state-panel" role="status"><span className="loading-mark" />Loading governed segment</div> : segments.length ? <section className="evidence-section split"><DeferredChart option={option} label={`Observed churn by ${dimension.replace('_', ' ')}`} /><div className="segment-ledger">{segments.slice(0, 10).map((row) => <EvidenceRow key={row.segment_key || row.engagement_segment} label={row.segment_label || row.engagement_segment || 'Unknown'} value={percent.format(row.observed_churn_rate)} note={`${integer.format(row.eligible_subscribers)} eligible`} />)}</div></section> : <EmptyState title="No eligible segments" body="No segment meets the governed minimum group size for this window." />}</div>
}

function DefinitionsView({ definitions }: { definitions: Definition[] }) {
  return <div className="view-stack"><section className="ledger-opening"><div><p className="section-kicker">Governed contract</p><h1>Metric definitions</h1></div><p className="opening-brief">Definitions come from the governed semantic model and remain identical across API, export, and interface.</p></section><section className="definition-list">{definitions.map((item) => <article key={item.metric_id}><div><code>{item.metric_id}</code><h2>{item.metric_id.replaceAll('_', ' ')}</h2></div><p>{item.definition}</p><dl><div><dt>Grain</dt><dd>{item.grain}</dd></div><div><dt>Direction</dt><dd>{item.direction}</dd></div><div><dt>Limitation</dt><dd>{item.limitation}</dd></div></dl></article>)}</section></div>
}

function EvidenceRow({ label, value, note }: { label: string; value: string; note?: string }) { return <div className="evidence-row"><span>{label}{note && <small>{note}</small>}</span><strong>{value}</strong></div> }
function DefinitionBrief({ title, body }: { title: string; body: string }) { return <div className="definition-brief"><strong>{title}</strong><p>{body}</p></div> }
function EmptyState({ title, body }: { title: string; body: string }) { return <div className="empty-state"><span aria-hidden="true">∅</span><div><strong>{title}</strong><p>{body}</p></div></div> }

export default App
