export function createSessionId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `intervai-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function detectPressureQuestion(text = '') {
  const normalized = text.toLowerCase()
  const markers = [
    'challenge your own decision',
    'strongest assumption',
    'credible alternative',
    'suppose one important assumption',
    'now add a production constraint',
    'what would make you change',
    'under what conditions would',
    'what breaks first',
  ]

  return markers.some((marker) => normalized.includes(marker))
}

export function missionSignal(candidate) {
  if (!candidate) return { label: 'No profile', value: '—' }

  const signals = candidate.signals || {}
  const completed = Number(signals.missionsCompleted || 0)
  const firstTry = Number(signals.missionsFirstTry || 0)
  const ratio = completed > 0 ? Math.round((firstTry / completed) * 100) : 0

  return {
    label: 'First-try rate',
    value: `${ratio}%`,
  }
}

export function getCandidateRiskSignals(candidate) {
  const missions = candidate?.missions || []
  const repeated = missions.filter((mission) => mission.passed && Number(mission.attempts || 0) >= 4).length
  const failed = missions.filter((mission) => mission.passed === false).length
  const skipped = missions.filter((mission) => mission.skipped).length

  return { repeated, failed, skipped }
}
