import { useState } from 'react'

export default function AnswerComposer({ disabled, onSubmit }) {
  const [answer, setAnswer] = useState('')

  async function send() {
    const cleaned = answer.trim()
    if (!cleaned || disabled) return
    const sent = await onSubmit(cleaned)
    if (sent) setAnswer('')
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  return (
    <div className="composer">
      <textarea
        rows="4"
        value={answer}
        disabled={disabled}
        onChange={(event) => setAnswer(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Explain your reasoning. You can discuss trade-offs, implementation details, and failure modes…"
        aria-label="Candidate answer"
      />
      <div className="composer__footer">
        <span>Enter to send · Shift + Enter for a new line</span>
        <button type="button" className="primary-button primary-button--compact" onClick={send} disabled={disabled || !answer.trim()}>
          {disabled ? 'Thinking…' : 'Submit answer'}
        </button>
      </div>
    </div>
  )
}
