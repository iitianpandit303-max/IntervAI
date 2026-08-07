export async function loadCandidates() {
  const response = await fetch('/data/candidates.json')

  if (!response.ok) {
    throw new Error('Candidate profiles could not be loaded.')
  }

  const payload = await response.json()
  return Array.isArray(payload.candidates) ? payload.candidates : []
}
