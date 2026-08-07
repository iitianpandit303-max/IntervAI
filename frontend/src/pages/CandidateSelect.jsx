import { useEffect, useState } from 'react'
import { loadCandidates } from '../api/candidateApi'
import CandidatePicker from '../components/candidate/CandidatePicker'
import { getCandidateRiskSignals, missionSignal } from '../utils/interviewUi'

export default function CandidateSelect({ onStart, busy, error }) {
  const [candidates, setCandidates] = useState([])
  const [selected, setSelected] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    loadCandidates()
      .then((items) => {
        setCandidates(items)
        if (items.length) setSelected(items[0])
      })
      .catch((candidateError) => setLoadError(candidateError.message))
  }, [])

  const firstTry = missionSignal(selected)
  const risk = getCandidateRiskSignals(selected)

  return (
    <main className="landing-shell">
      <section className="hero-panel">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">IA</span>
          <span>
            <strong>IntervAI</strong>
            <small>ABTalks AI Cohort</small>
          </span>
        </div>

        <div className="hero-copy">
          <p className="eyebrow">Adaptive technical interview engine</p>
          <h1>Not a question list.<br />An interviewer that reacts.</h1>
          <p className="hero-description">
            Candidate history shapes the starting strategy. Answers change the depth, follow-ups, and engineering pressure in real time.
          </p>
        </div>

        <div className="capability-grid">
          <div><strong>8+</strong><span>questions</span></div>
          <div><strong>4+</strong><span>curriculum days</span></div>
          <div><strong>Live</strong><span>adaptive follow-ups</span></div>
        </div>

        <div className="hero-note">
          <span className="note-icon">↗</span>
          <p><strong>How the demo works</strong><br />Select any supplied cohort profile. IntervAI uses attempts, skips, failures, role and experience as interview priors.</p>
        </div>
      </section>

      <section className="selection-panel">
        <div className="selection-panel__header">
          <div>
            <p className="eyebrow">Step 01</p>
            <h2>Choose a candidate</h2>
          </div>
          <span className="profile-count">{candidates.length || '—'} profiles</span>
        </div>

        {(loadError || error) && <div className="error-banner">{loadError || error}</div>}

        <CandidatePicker
          candidates={candidates}
          selectedId={selected?.member?.id}
          onSelect={setSelected}
        />

        {selected && (
          <div className="candidate-preview">
            <div className="candidate-preview__top">
              <div>
                <span className="candidate-id">{selected.member.id}</span>
                <h3>{selected.member.name}</h3>
                <p>{selected.member.jobRole} · {selected.member.yearsExperience} years experience</p>
              </div>
              <span className="ready-pill">Ready</span>
            </div>
            <div className="candidate-metrics">
              <div><span>Commits</span><strong>{selected.signals.commitDays}/31</strong></div>
              <div><span>{firstTry.label}</span><strong>{firstTry.value}</strong></div>
              <div><span>Diagnostic signals</span><strong>{risk.repeated + risk.failed}</strong></div>
            </div>
          </div>
        )}

        <button
          type="button"
          className="primary-button start-button"
          disabled={!selected || busy}
          onClick={() => onStart(selected)}
        >
          <span>{busy ? 'Creating interview…' : 'Start adaptive interview'}</span>
          <span aria-hidden="true">→</span>
        </button>
      </section>
    </main>
  )
}
