export default function StruggledQuestions({ questions = [] }) {
  return (
    <section className="report-panel struggled-panel">
      <div className="report-panel__header">
        <div>
          <span className="section-kicker">Diagnostic replay</span>
          <h2>Questions that exposed gaps</h2>
        </div>
        <span className="panel-count">{questions.length}</span>
      </div>

      {questions.length ? (
        <div className="struggled-list">
          {questions.map((item) => (
            <article key={item.question_id}>
              <div className="struggled-top">
                <span>Day {item.day}</span>
                <strong>{Math.round(item.score)}/100</strong>
              </div>
              <h3>{item.question}</h3>
              <p>{item.reason}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="report-empty">No questions crossed the struggled-question threshold.</p>
      )}
    </section>
  )
}
