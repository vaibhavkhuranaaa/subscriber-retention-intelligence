import { useEffect, useState } from 'react'
import { type Journey, type Subscriber, type WindowId, get } from './api'

const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 })
const integer = new Intl.NumberFormat('en-US')

export default function SubscriberView({ windowId }: { windowId: WindowId }) {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([])
  const [journey, setJourney] = useState<Journey | null>(null)
  const [selectedToken, setSelectedToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setSubscribers([])
    setSelectedToken(null)
    setJourney(null)
    get<Subscriber[]>(`/api/v1/subscribers?label_window=${windowId}&limit=20`, controller.signal)
      .then((payload) => setSubscribers(payload.data))
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [windowId])

  useEffect(() => {
    if (!selectedToken) return
    const controller = new AbortController()
    setJourney(null)
    setError(null)
    get<Journey>(`/api/v1/subscribers/${selectedToken.toLowerCase()}?label_window=${windowId}`, controller.signal)
      .then((payload) => setJourney(payload.data))
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason.message)
      })
    return () => controller.abort()
  }, [selectedToken, windowId])

  return <div className="view-stack">
    <section className="ledger-opening"><div><p className="section-kicker">Private journey review</p><h1>Pseudonymous records connect outcome to prior evidence.</h1></div><p className="opening-brief">Records are sorted by 90-day gross receipts for inspection, not intervention priority. No model score exists in M5.</p></section>
    {error && <div className="state-panel error" role="alert"><strong>Private evidence unavailable</strong><p>{error}</p></div>}
    {!error && <section className="journey-layout"><div className="subscriber-list" aria-label="Subscriber records">{!loading && subscribers.length > 0 && <div className="subscriber-header" aria-hidden="true"><span>Token</span><span>Engagement</span><span>Receipts · 90d</span><span>Outcome</span></div>}{loading ? <div className="list-state" role="status"><span className="loading-mark" />Loading private records</div> : subscribers.length ? subscribers.map((row) => <button key={row.subscriber_token} className={selectedToken === row.subscriber_token ? 'subscriber-row active' : 'subscriber-row'} onClick={() => setSelectedToken(row.subscriber_token)}><span className="token">{row.subscriber_token.slice(0, 8)}…{row.subscriber_token.slice(-4)}</span><span>{row.engagement_segment}</span><span>{compact.format(row.gross_receipts_90d)}</span><strong className={row.is_churn ? 'outcome churned' : 'outcome renewed'}>{row.is_churn ? 'Churned' : 'Renewed'}</strong></button>) : <EmptyState title="No private records" body="No bounded review records exist for this label window." />}</div><div className="journey-detail">{!selectedToken && <EmptyState title="Choose a private record" body="Select one pseudonymous subscriber to inspect cutoff-safe history." />}{selectedToken && !journey && <div className="state-panel" role="status"><span className="loading-mark" />Loading bounded journey</div>}{journey && <><div className="journey-heading"><div><p className="section-kicker">Subscriber token</p><h2>{String(journey.profile.subscriber_token).slice(0, 12)}…</h2></div><strong className={journey.profile.is_churn ? 'outcome churned' : 'outcome renewed'}>{journey.profile.is_churn ? 'Observed churn' : 'Observed renewal'}</strong></div><div className="journey-facts"><EvidenceRow label="Effective expiration" value={String(journey.profile.effective_expiration_date)} /><EvidenceRow label="Engagement segment" value={String(journey.profile.engagement_segment)} /><EvidenceRow label="Listening active days · 30d" value={integer.format(Number(journey.profile.listening_active_days_30d))} /><EvidenceRow label="Gross receipts · 90d" value={compact.format(Number(journey.profile.gross_receipts_90d))} /></div><h3>Latest subscription events</h3><div className="event-list">{journey.transactions.slice(0, 8).map((event, index) => <div key={`${event.transaction_date}-${index}`}><time>{String(event.transaction_date)}</time><span>{event.is_cancel ? 'Cancellation' : `${event.payment_plan_days}-day subscription`}</span><strong>{compact.format(Number(event.actual_amount_paid))}</strong></div>)}</div></>}</div></section>}
  </div>
}

function EvidenceRow({ label, value }: { label: string; value: string }) {
  return <div className="evidence-row"><span>{label}</span><strong>{value}</strong></div>
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return <div className="empty-state"><span aria-hidden="true">∅</span><div><strong>{title}</strong><p>{body}</p></div></div>
}
