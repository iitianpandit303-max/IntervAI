export default function InterviewComplete({ candidate, feedback, questionCount, onReset }) {
  return (
    <main className="complete-shell">
      <section className="complete-card">
        <div className="complete-icon">✓</div>
        <p className="eyebrow">Interview complete</p>
        <h1>{candidate.member.name}'s session is ready for review.</h1>
        <p className="complete-summary">
          {feedback?.summary || `IntervAI completed ${questionCount} questions and generated structured feedback.`}
        </p>

        <div className="complete-grid">
          <div><span>Questions asked</span><strong>{questionCount}</strong></div>
          <div><span>Minimum target</span><strong>8+</strong></div>
          <div><span>Feedback</span><strong>{feedback ? 'Generated' : 'Ready'}</strong></div>
        </div>

        {feedback && (
          <div className="report-preview">
            <div>
              <span>Strength signal</span>
              <p>{feedback.strengths?.[0] || 'See the full readiness report for detailed mastery evidence.'}</p>
            </div>
            <div>
              <span>Next action</span>
              <p>{feedback.next?.[0] || 'Review the structured readiness report.'}</p>
            </div>
          </div>
        )}

        <p className="commit-note">The full Knowledge Map and visual Readiness Report arrive in the next UI milestone.</p>
        <button className="secondary-button" type="button" onClick={onReset}>Run another candidate</button>
      </section>
    </main>
  )
}
