import { useEffect, useRef } from 'react'
import AnswerComposer from '../components/interview/AnswerComposer'
import InterviewMessage from '../components/interview/InterviewMessage'
import InterviewProgress from '../components/interview/InterviewProgress'

export default function InterviewRoom({ interview }) {
  const endRef = useRef(null)
  const candidate = interview.candidate
  const busy = interview.status === 'loading'

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [interview.messages, busy])

  return (
    <main className="interview-shell">
      <aside className="interview-sidebar">
        <div className="brand-lockup brand-lockup--compact">
          <span className="brand-mark" aria-hidden="true">IA</span>
          <span><strong>IntervAI</strong><small>Interview session</small></span>
        </div>

        <div className="candidate-mini-card">
          <span className="candidate-avatar candidate-avatar--large">
            {candidate.member.name.split(' ').slice(0, 2).map((part) => part[0]).join('')}
          </span>
          <div>
            <span className="candidate-id">{candidate.member.id}</span>
            <h3>{candidate.member.name}</h3>
            <p>{candidate.member.jobRole}</p>
          </div>
        </div>

        <InterviewProgress
          questionCount={interview.questionCount}
          pressureMode={interview.pressureMode}
        />

        <div className="session-facts">
          <div><span>Experience</span><strong>{candidate.member.yearsExperience} years</strong></div>
          <div><span>Completed</span><strong>{candidate.signals.missionsCompleted}/31</strong></div>
          <div><span>Commit days</span><strong>{candidate.signals.commitDays}/31</strong></div>
        </div>

        <div className="sidebar-note">
          <span>AI</span>
          <p>Questions are grounded in the supplied cohort curriculum and this candidate's learning history.</p>
        </div>
      </aside>

      <section className="interview-main">
        <header className="interview-header">
          <div>
            <p className="eyebrow">Live technical interview</p>
            <h1>AI Engineering</h1>
          </div>
          <div className="live-status"><span /> Session active</div>
        </header>

        <div className="mobile-progress">
          <InterviewProgress
            questionCount={interview.questionCount}
            pressureMode={interview.pressureMode}
          />
        </div>

        <div className="conversation" aria-live="polite">
          {interview.messages.map((message) => (
            <InterviewMessage
              key={message.id}
              message={message}
              candidateName={candidate.member.name.split(' ')[0]}
            />
          ))}

          {busy && (
            <div className="thinking-row">
              <span /><span /><span />
              <p>Evaluating your answer and deciding the next move…</p>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {interview.error && <div className="error-banner interview-error">{interview.error}</div>}

        <div className="composer-wrap">
          <AnswerComposer disabled={busy} onSubmit={interview.submitAnswer} />
        </div>
      </section>
    </main>
  )
}
