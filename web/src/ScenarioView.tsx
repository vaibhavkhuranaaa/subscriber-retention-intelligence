import { useState, type Dispatch, type FormEvent, type SetStateAction } from 'react'
import { post, type Scenario, type ScenarioInputs } from './api'

const integer = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })
const percent = new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1 })
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 })

function Input({ id, label, help, value, min, max, step, onChange }: {
  id: keyof ScenarioInputs
  label: string
  help: string
  value: number
  min: number
  max: number
  step: number
  onChange: (id: keyof ScenarioInputs, value: number) => void
}) {
  return <label className="assumption-field" htmlFor={id}>
    <span>{label}</span>
    <input id={id} name={id} type="number" value={value} min={min} max={max} step={step} onChange={(event) => {
      const nextValue = event.currentTarget.valueAsNumber
      if (Number.isFinite(nextValue)) onChange(id, nextValue)
    }} required />
    <small>{help}</small>
  </label>
}

function SensitivityPlot({ scenario }: { scenario: Scenario }) {
  const rows = (['low', 'expected', 'high'] as const).map((key) => ({ key, value: scenario.outcomes[key] }))
  const magnitudeScale = Math.max(...rows.map((row) => Math.abs(row.value.simulated_net_value)), 1)
  const expected = scenario.outcomes.expected

  return <section className="sensitivity-plot" aria-labelledby="sensitivity-title">
    <div className="plot-heading">
      <div><p>Assumption range</p><h2 id="sensitivity-title">Net gross-receipt proxy by assumed lift</h2></div>
      <dl>
        <div><dt>Break-even lift</dt><dd>{expected.break_even_lift === null ? 'Not defined' : percent.format(expected.break_even_lift)}</dd></div>
        <div><dt>Assumed spend</dt><dd>{compact.format(expected.total_spend)}</dd></div>
      </dl>
    </div>
    <div className="plot-body">
      {rows.map(({ key, value }) => {
        const label = key === 'expected' ? 'Base' : key[0].toUpperCase() + key.slice(1)
        const barScale = Math.max(0.02, Math.abs(value.simulated_net_value) / magnitudeScale)
        return <div className={`sensitivity-row ${key} ${value.simulated_net_value < 0 ? 'negative' : ''}`} key={key} aria-label={`${label}, ${percent.format(value.assumed_lift)} assumed lift, ${compact.format(value.simulated_net_value)} net gross-receipt proxy`}>
          <span className="case-label">{label}</span>
          <span className="lift-label">{percent.format(value.assumed_lift)}</span>
          <span className="bar-track" aria-hidden="true"><span className="bar-fill" style={{ transform: `scaleX(${barScale})` }} /></span>
          <strong>{compact.format(value.simulated_net_value)}</strong>
        </div>
      })}
    </div>
  </section>
}

export default function ScenarioView({ inputs, setInputs, scenario, setScenario }: {
  inputs: ScenarioInputs
  setInputs: Dispatch<SetStateAction<ScenarioInputs>>
  scenario: Scenario | null
  setScenario: Dispatch<SetStateAction<Scenario | null>>
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = (id: keyof ScenarioInputs, value: number) => {
    setInputs((current) => ({ ...current, [id]: value }))
    setScenario(null)
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const response = await post<Scenario>('/api/v1/scenario', inputs)
      setScenario(response.data)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Scenario unavailable')
    } finally {
      setLoading(false)
    }
  }

  const expected = scenario?.outcomes.expected
  return <div className="view-stack scenario-view">
    <section className="scenario-workbench">
      <div className="scenario-results" aria-live="polite">
        <header className="scenario-header">
          <p className="section-kicker">Intervention scenario</p>
          <div className="scenario-title-row">
            <h1>{integer.format(inputs.capacity)}-contact scenario</h1>
            <strong className="simulation-stamp">Simulated</strong>
          </div>
          <p>Historical risk prioritization with user-assumed lift and cost. This is sensitivity analysis, not a measured treatment effect.</p>
        </header>

        {error && <div className="scenario-error" role="alert"><strong>Scenario unavailable</strong><p>{error}</p></div>}
        {!error && !scenario && <div className="scenario-empty"><strong>No result for these assumptions</strong><p>Run the scenario to calculate the selected population, spend, and sensitivity range.</p></div>}
        {scenario && expected && <>
          <div className="result-status"><span>Repeat subscribers only · March 2017 score window</span><span>89,259 March-new subscribers excluded</span></div>
          <SensitivityPlot scenario={scenario} />
          <section className="scenario-metrics" aria-label="Scenario result measures">
            <div><span>Selected contacts</span><strong>{integer.format(scenario.selection.contacts)}</strong><small>{scenario.selection.capacity_utilization === null ? 'Not defined at zero capacity' : `${percent.format(scenario.selection.capacity_utilization)} capacity used`}</small></div>
            <div><span>Modeled churn exposure</span><strong>{integer.format(scenario.selection.expected_churners)}</strong><small>{percent.format(scenario.selection.modeled_risk_capture)} eligible risk captured</small></div>
            <div><span>Simulated retained</span><strong>{integer.format(expected.simulated_retained_subscribers)}</strong><small>At {percent.format(expected.assumed_lift)} assumed lift</small></div>
            <div className={expected.simulated_net_value >= 0 ? 'net-positive' : 'net-negative'}><span>Net gross-receipt proxy</span><strong>{compact.format(expected.simulated_net_value)}</strong><small>After {compact.format(expected.total_spend)} assumed spend</small></div>
          </section>
          <section className="scenario-audit">
            <p className="section-kicker">Selection audit</p>
            <dl>
              <div><dt>Capacity used</dt><dd>{scenario.selection.capacity_utilization === null ? 'Not defined' : percent.format(scenario.selection.capacity_utilization)}</dd></div>
              <div><dt>Eligible risk captured</dt><dd>{percent.format(scenario.selection.modeled_risk_capture)}</dd></div>
              <div><dt>Observed holdout churn</dt><dd>{percent.format(scenario.selection.observed_churn_rate)}</dd></div>
              <div><dt>March-new subscribers</dt><dd>Excluded</dd></div>
            </dl>
            <p>{scenario.definitions.value_proxy}</p>
          </section>
          <p className="scenario-limitation">{scenario.definitions.limitation} Assumed lift range is sensitivity analysis, not a probability interval.</p>
        </>}
      </div>

      <form className="assumption-panel" onSubmit={submit}>
        <div className="assumption-heading"><p>Controls</p><h2>Scenario assumptions</h2></div>
        <fieldset>
          <legend>Selection constraints</legend>
          <Input id="capacity" label="Contact capacity" help="100 to 881,701 repeat subscribers" value={inputs.capacity} min={100} max={881701} step={100} onChange={update} />
          <Input id="minimum_score" label="Minimum calibrated risk" help="Historical churn probability threshold" value={inputs.minimum_score} min={0} max={1} step={0.01} onChange={update} />
        </fieldset>
        <fieldset>
          <legend>Economic assumptions</legend>
          <Input id="contact_cost" label="Contact cost" help="Source-currency cost per selected contact" value={inputs.contact_cost} min={0} max={10000} step={0.1} onChange={update} />
          <Input id="offer_cost" label="Offer cost" help="Applied to every contact; acceptance is unknown" value={inputs.offer_cost} min={0} max={10000} step={0.1} onChange={update} />
          <Input id="assumed_lift" label="Assumed retention lift" help="Share of modeled churn prevented" value={inputs.assumed_lift} min={0} max={1} step={0.01} onChange={update} />
          <Input id="lift_uncertainty" label="Lift sensitivity ±" help="User-assumed range, not confidence interval" value={inputs.lift_uncertainty} min={0} max={0.5} step={0.01} onChange={update} />
        </fieldset>
        <button className="run-scenario" type="submit" disabled={loading}>{loading ? 'Calculating scenario' : 'Run simulated scenario'}</button>
        <p className="assumption-note"><strong>Interpretation limit</strong> Lift is an assumption. Latest payment is a gross-receipt proxy, not revenue, margin, or CLV.</p>
      </form>
    </section>
  </div>
}
