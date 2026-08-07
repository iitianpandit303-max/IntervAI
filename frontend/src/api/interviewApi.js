const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export async function interviewTurn(payload) {
  const response = await fetch(`${API_BASE_URL}/api/interview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Interview request failed.' }))
    throw new Error(error.detail || 'Interview request failed.')
  }

  return response.json()
}
