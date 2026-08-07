function ReportList({ title, eyebrow, items, emptyText }) {
  return (
    <section className="report-panel report-list-panel">
      <div className="report-panel__header">
        <div>
          <span className="section-kicker">{eyebrow}</span>
          <h2>{title}</h2>
        </div>
      </div>
      <ul className="report-list">
        {(items?.length ? items : [emptyText]).map((item, index) => (
          <li key={`${title}-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{item}</p></li>
        ))}
      </ul>
    </section>
  )
}

export default function ReportLists({ report }) {
  return (
    <div className="report-list-grid">
      <ReportList
        eyebrow="What held up"
        title="Strengths"
        items={report?.strengths}
        emptyText="No high-confidence strengths were recorded yet."
      />
      <ReportList
        eyebrow="What to repair"
        title="Gaps"
        items={report?.gaps}
        emptyText="No material gaps were recorded."
      />
      <ReportList
        eyebrow="Preparation plan"
        title="Next moves"
        items={report?.suggested_next_steps}
        emptyText="Continue practicing curriculum-grounded technical explanations."
      />
    </div>
  )
}
