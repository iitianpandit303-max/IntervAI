import { useMemo, useState } from 'react'
import { getCandidateRiskSignals, missionSignal } from '../../utils/interviewUi'

export default function CandidatePicker({ candidates, selectedId, onSelect }) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return candidates

    return candidates.filter((candidate) => {
      const member = candidate.member || {}
      return [member.name, member.jobRole, member.education, member.id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized))
    })
  }, [candidates, query])

  return (
    <div className="candidate-picker">
      <label className="search-field">
        <span>Find a candidate</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Name, role, candidate ID…"
        />
      </label>

      <div className="candidate-list" role="listbox" aria-label="Candidate profiles">
        {filtered.map((candidate) => {
          const member = candidate.member
          const selected = selectedId === member.id
          const risk = getCandidateRiskSignals(candidate)
          const firstTry = missionSignal(candidate)

          return (
            <button
              className={`candidate-row ${selected ? 'candidate-row--selected' : ''}`}
              key={member.id}
              type="button"
              role="option"
              aria-selected={selected}
              onClick={() => onSelect(candidate)}
            >
              <span className="candidate-avatar" aria-hidden="true">
                {member.name
                  .split(' ')
                  .slice(0, 2)
                  .map((part) => part[0])
                  .join('')}
              </span>
              <span className="candidate-row__main">
                <span className="candidate-row__name">{member.name}</span>
                <span className="candidate-row__role">{member.jobRole}</span>
                <span className="candidate-row__signals">
                  {member.yearsExperience}y exp · {firstTry.value} first-try
                  {(risk.failed || risk.skipped) > 0
                    ? ` · ${risk.failed + risk.skipped} gap signal${risk.failed + risk.skipped === 1 ? '' : 's'}`
                    : ''}
                </span>
              </span>
              <span className="candidate-row__arrow" aria-hidden="true">→</span>
            </button>
          )
        })}

        {filtered.length === 0 && (
          <div className="empty-state">No candidate matches “{query}”.</div>
        )}
      </div>
    </div>
  )
}
