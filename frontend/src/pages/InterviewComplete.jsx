import KnowledgeMap from '../components/knowledge/KnowledgeMap'
import ReportLists from '../components/report/ReportLists'
import ScoreBreakdown from '../components/report/ScoreBreakdown'
import StruggledQuestions from '../components/report/StruggledQuestions'

function TopicPills({ title, items = [], tone = 'default' }) {
  return (
    <div className="topic-cluster">
      <span>{title}</span>
      <div className="topic-pills">
        {items.length ? items.map((item) => (
          <strong className={`topic-pill topic-pill--${tone}`} key={item}>{item}</strong>
        )) : <em>Not enough evidence</em>}
      </div>
    </div>
  )
}

export default function InterviewComplete({ candidate, feedback, questionCount, insights, onReset }) {
  const report = insights?.finalReport
  const knowledgeMap = insights?.knowledgeMap
  const score = Math.round(report?.overall_score || 0)
  const confidence = Math.round((report?.report_confidence || 0) * 100)

  if (!report) {
    return (
      <main className="complete-shell">
        <section className="complete-card">
          <div className="complete-icon">✓</div>
          <p className="eyebrow">Interview complete</p>
          <h1>{candidate.member.name}'s session is ready for review.</h1>
          <p className="complete-summary">{feedback?.summary || `IntervAI completed ${questionCount} questions and generated structured feedback.`}</p>
          <div className="report-preview">
            <div><span>Strength signal</span><p>{feedback?.strengths?.[0] || 'Structured feedback generated.'}</p></div>
            <div><span>Next action</span><p>{feedback?.next?.[0] || 'Review the candidate preparation plan.'}</p></div>
          </div>
          <button className="secondary-button" type="button" onClick={onReset}>Run another candidate</button>
        </section>
      </main>
    )
  }

  return (
    <main className="report-shell">
      <header className="report-topbar">
        <div className="brand-lockup brand-lockup--compact">
          <span className="brand-mark" aria-hidden="true">IA</span>
          <span><strong>IntervAI</strong><small>Readiness report</small></span>
        </div>
        <button className="secondary-button" type="button" onClick={onReset}>Run another candidate</button>
      </header>

      <section className="report-hero">
        <div className="report-hero__copy">
          <p className="eyebrow">Interview readiness report · {candidate.member.id}</p>
          <h1>{candidate.member.name}</h1>
          <p>{candidate.member.jobRole} · {candidate.member.yearsExperience} years experience</p>
          <div className="readiness-badge">{report.readiness_level}</div>
        </div>

        <div className="overall-score" style={{ '--score': `${score * 3.6}deg` }}>
          <div><strong>{score}</strong><span>overall</span></div>
        </div>

        <div className="report-hero__stats">
          <div><span>Evidence confidence</span><strong>{confidence}%</strong></div>
          <div><span>Questions answered</span><strong>{report.answered_questions}</strong></div>
          <div><span>Days covered</span><strong>{report.curriculum_days_covered?.length || 0}</strong></div>
          <div><span>Pressure challenges</span><strong>{report.pressure_challenges_used}</strong></div>
        </div>
      </section>

      <section className="report-grid report-grid--top">
        <ScoreBreakdown report={report} />
        <section className="report-panel topic-panel">
          <div className="report-panel__header">
            <div><span className="section-kicker">Signal summary</span><h2>Where the candidate stands</h2></div>
          </div>
          <TopicPills title="Strongest" items={report.strongest_topics} tone="strong" />
          <TopicPills title="Weakest" items={report.weakest_topics} tone="weak" />
          <TopicPills title="Revise" items={report.topics_to_revise} tone="revise" />
          <div className="revisit-days">
            <span>Curriculum days to revisit</span>
            <div>{report.curriculum_days_to_revisit?.length ? report.curriculum_days_to_revisit.map((day) => <strong key={day}>Day {day}</strong>) : <em>None flagged</em>}</div>
          </div>
        </section>
      </section>

      <KnowledgeMap map={knowledgeMap} />
      <StruggledQuestions questions={report.struggled_questions} />
      <ReportLists report={report} />

      <footer className="report-footer">
        <p>{feedback?.summary}</p>
        <button className="secondary-button" type="button" onClick={onReset}>Interview another candidate</button>
      </footer>
    </main>
  )
}
