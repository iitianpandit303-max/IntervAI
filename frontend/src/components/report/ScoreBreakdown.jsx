const dimensions = [
  ['Technical accuracy', 'technical_accuracy'],
  ['Conceptual understanding', 'conceptual_understanding'],
  ['Engineering reasoning', 'engineering_reasoning'],
  ['Communication quality', 'communication_quality'],
  ['Answer depth', 'answer_depth'],
]

export default function ScoreBreakdown({ report }) {
  return (
    <section className="report-panel">
      <div className="report-panel__header">
        <div>
          <span className="section-kicker">Evaluation rubric</span>
          <h2>Interview dimensions</h2>
        </div>
      </div>
      <div className="score-breakdown">
        {dimensions.map(([label, key]) => {
          const score = Math.round(report?.[key] || 0)
          return (
            <div className="score-row" key={key}>
              <div className="score-row__copy"><span>{label}</span><strong>{score}</strong></div>
              <div className="score-row__track"><span style={{ width: `${score}%` }} /></div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
