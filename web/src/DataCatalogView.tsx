const datasetUrl = 'https://huggingface.co/datasets/vaibhavkhurana/subscriber-retention-intelligence'

const tables = [
  { name: 'Member', path: 'member', split: 'full', grain: 'One row per subscriber', rows: 6_769_473, files: 1, bytes: 60_491_935, fields: 'Pseudonymous key, city, age band, gender, registration method and month' },
  { name: 'Subscription transaction', path: 'subscription_transaction', split: 'full', grain: 'One row per accepted transaction', rows: 22_975_416, files: 2, bytes: 463_554_548, fields: 'Plan, payment, renewal, cancellation and effective membership dates' },
  { name: 'Churn label', path: 'churn_label', split: '2017_02', grain: 'One subscriber per label window', rows: 1_963_891, files: 2, bytes: 15_720_822, fields: 'February and March 2017 observed churn labels' },
  { name: 'Listening day', path: 'listening_day', split: 'full', grain: 'One subscriber activity day', rows: 410_502_905, files: 27, bytes: 6_982_487_551, fields: 'Completion buckets, unique plays, listening seconds and quality flag' },
]

const integer = new Intl.NumberFormat('en-US')
const bytes = new Intl.NumberFormat('en-US', { style: 'unit', unit: 'gigabyte', maximumFractionDigits: 2 })

export default function DataCatalogView() {
  const manifestUrl = `${datasetUrl}/resolve/main/manifest.json`
  return <div className="view-stack data-catalog">
    <section className="ledger-opening">
      <div><p className="section-kicker">Row-level analytical release</p><h1>Detailed data catalog</h1></div>
      <p className="opening-brief">The public release preserves accepted analytical rows in compressed Parquet. Subscriber keys are release-specific pseudonyms; source identifiers are not published.</p>
    </section>

    <section className="release-register" aria-labelledby="release-register-title">
      <div className="release-heading">
        <div><span>Release register</span><h2 id="release-register-title">public-m12</h2></div>
        <div className="release-links">
          <a href={datasetUrl}>Browse full dataset</a>
          <a href={manifestUrl}>Open manifest</a>
        </div>
      </div>
      <dl className="release-totals">
        <div><dt>Rows</dt><dd>{integer.format(442_211_685)}</dd></div>
        <div><dt>Parquet files</dt><dd>32</dd></div>
        <div><dt>Compressed payload</dt><dd>{bytes.format(7.522254856)}</dd></div>
        <div><dt>Format</dt><dd>Parquet · Zstd</dd></div>
      </dl>
      <div className="table-wrap data-table-wrap" tabIndex={0} aria-label="Scrollable detailed data catalog">
        <table>
          <thead><tr><th>Dataset</th><th>Grain</th><th>Rows</th><th>Files</th><th>Compressed</th><th>Published fields</th></tr></thead>
          <tbody>{tables.map((table) => <tr key={table.path}>
            <td><a href={`${datasetUrl}/viewer/${table.path}/${table.split}`}><strong>{table.name}</strong></a><code>{table.path}</code></td>
            <td>{table.grain}</td>
            <td>{integer.format(table.rows)}</td>
            <td>{table.files}</td>
            <td>{bytes.format(table.bytes / 1_000_000_000)}</td>
            <td>{table.fields}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>

    <section className="release-notes" aria-label="Detailed release boundaries">
      <div><span>Identity</span><p>Subscriber and transaction identifiers use release-specific, collision-checked 64-bit one-way pseudonyms. The private salt is not distributed.</p></div>
      <div><span>Generalization</span><p>Exact age is reduced to a 10-year band and exact registration date to month. Implausible age values are null.</p></div>
      <div><span>Coverage</span><p>All accepted member, transaction, churn-label and listening-day rows are included. This is not an aggregate extract.</p></div>
      <div><span>Interpretation</span><p>Payment fields are source receipts, not recognized revenue. Churn labels are observed outcomes, not treatment effects.</p></div>
    </section>
  </div>
}
